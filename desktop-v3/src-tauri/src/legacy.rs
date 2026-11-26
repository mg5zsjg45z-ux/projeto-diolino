//! Read-only projection of the version 8 database used by Diolino 2.x.
use chrono::{DateTime, Days, Local, NaiveDate};
use rusqlite::{params, Connection, OpenFlags, Params};
use serde_json::{json, Value};
use std::{collections::BTreeMap, path::Path, time::Duration};

fn query(conn: &Connection, sql: &str, args: impl Params) -> Result<Vec<Value>, String> {
    let mut statement = conn
        .prepare(sql)
        .map_err(|_| "Estrutura do banco 2.x incompatível.")?;
    let rows = statement
        .query_map(args, |row| row.get::<_, String>(0))
        .map_err(|_| "Não foi possível consultar o banco 2.x.")?;
    rows.map(|row| {
        let raw = row.map_err(|_| "Falha na leitura do banco 2.x.")?;
        serde_json::from_str(&raw).map_err(|_| "Registro inválido no banco 2.x.".into())
    })
    .collect()
}

pub fn read(
    path: &Path,
    day: &str,
    days: u32,
    start: Option<&str>,
    end: Option<&str>,
) -> Result<Value, String> {
    let date = |raw: &str| NaiveDate::parse_from_str(raw, "%Y-%m-%d").map_err(|_| "Data inválida.");
    let selected = date(day)?;
    let first = selected
        .checked_sub_days(Days::new(u64::from(days) - 1))
        .ok_or("Período inválido.")?;
    let lower = start.map(date).transpose()?.unwrap_or(first);
    let upper = end.map(date).transpose()?.unwrap_or(selected);
    if upper < lower || (upper - lower).num_days() > 400 {
        return Err("Período inválido.".into());
    }
    let start = first.to_string();
    let conn = Connection::open_with_flags(path, OpenFlags::SQLITE_OPEN_READ_ONLY)
        .map_err(|_| "Banco do Diolino 2.x ausente ou inacessível.")?;
    conn.busy_timeout(Duration::from_secs(3))
        .map_err(|_| "Banco 2.x ocupado.")?;
    conn.execute_batch("PRAGMA query_only=ON; BEGIN;")
        .map_err(|_| "Banco 2.x ocupado.")?;
    let version: i32 = conn
        .query_row("PRAGMA user_version", [], |r| r.get(0))
        .map_err(|_| "Não foi possível verificar a versão do banco.")?;
    if version != 8 {
        return Err("Banco incompatível. A leitura requer o esquema 8 do Diolino 2.x.".into());
    }
    let agenda = query(&conn, "SELECT json_object('id',id,'date',date,'time',time,'title',title,'state',state,'duration_min',duration_min)
        FROM agenda WHERE deleted_at IS NULL AND date BETWEEN ?1 AND ?2 ORDER BY date,coalesce(time,'99:99'),id",
        params![lower.to_string(), upper.to_string()])?;
    let study = query(&conn, "SELECT json_object('id',id,'date',date,'time',time,'topic',topic,'duration_min',duration_min,'format',format,
        'source',source,'learning',learning,'notes',notes) FROM study WHERE deleted_at IS NULL AND date BETWEEN ?1 AND ?2
        ORDER BY date DESC,time DESC,id DESC", params![start,day])?;
    let tasks = query(&conn, "SELECT json_object('id',s.id,'title',s.title,'plan',p.title,'state',s.state,'priority',s.priority,'due',s.due_date)
        FROM plan_steps s JOIN plans p ON p.id=s.plan_id WHERE s.deleted_at IS NULL AND p.deleted_at IS NULL AND p.status='Ativo'
        ORDER BY p.id,s.position,s.id", [])?;
    let study_points = query(
        &conn,
        "SELECT json_array(date,sum(duration_min)) FROM study
        WHERE deleted_at IS NULL AND date BETWEEN ?1 AND ?2 GROUP BY date ORDER BY date",
        params![start, day],
    )?;
    let exercise = query(
        &conn,
        "SELECT json_array(date,sum(duration_min)) FROM workout
        WHERE deleted_at IS NULL AND date BETWEEN ?1 AND ?2 GROUP BY date ORDER BY date",
        params![start, day],
    )?;
    let sleep = query(&conn, "SELECT json_array(date,sum((unixepoch(end)-unixepoch(start))/3600.0-awake_min/60.0)) FROM sleep
        WHERE deleted_at IS NULL AND date BETWEEN ?1 AND ?2 GROUP BY date ORDER BY date", params![start,day])?;
    let weight = query(&conn, "SELECT json_array(date,weight_kg) FROM (
        SELECT date,weight_kg,row_number() OVER(PARTITION BY date ORDER BY time DESC,id DESC) AS seq FROM body
        WHERE deleted_at IS NULL AND weight_kg IS NOT NULL AND date BETWEEN ?1 AND ?2) WHERE seq=1 ORDER BY date", params![start,day])?;
    let pref = |pattern: &str| {
        query(
            &conn,
            "SELECT json_array(key,value) FROM preferences WHERE key GLOB ?1 ORDER BY key",
            [pattern],
        )
    };
    let mut goals = BTreeMap::<String, (String, String)>::new();
    for pair in pref("habit_goal:*")? {
        let key = pair[0]
            .as_str()
            .unwrap_or_default()
            .split(':')
            .collect::<Vec<_>>();
        let value: Value =
            serde_json::from_str(pair[1].as_str().unwrap_or_default()).unwrap_or(Value::Null);
        if let ([_, id, effective], Some(name)) = (key.as_slice(), value["name"].as_str()) {
            if *effective <= day {
                let goal = goals
                    .entry(id.to_string())
                    .or_insert_with(|| (effective.to_string(), String::new()));
                goal.1 = name.to_owned();
            }
        }
    }
    let marks: BTreeMap<String, String> = pref("habit_day:*")?
        .into_iter()
        .filter_map(|v| Some((v[0].as_str()?.into(), v[1].as_str()?.into())))
        .collect();
    let habit_dates = dates(selected, 30)?;
    let habits: Vec<_> = goals
        .into_iter()
        .map(|(id, (first, name))| {
            let cells: Vec<_> = habit_dates
                .iter()
                .map(|d| {
                    let status = if d < &first {
                        "inactive"
                    } else {
                        match marks
                            .get(&format!("habit_day:{id}:{d}"))
                            .map(String::as_str)
                        {
                            Some("true") => "done",
                            Some("false") => "missed",
                            _ => "unknown",
                        }
                    };
                    json!([d, status])
                })
                .collect();
            json!({"id":id,"name":name,"cells":cells})
        })
        .collect();
    let now = Local::now();
    let mut pending = 0;
    let mut buckets = [0; 7];
    for pair in pref("review_card:*")? {
        let card: Value =
            serde_json::from_str(pair[1].as_str().unwrap_or_default()).unwrap_or(Value::Null);
        if card["area"] != "Medicina" || card["archived"] == true {
            continue;
        }
        let schedule: Value = serde_json::from_str(card["schedule"].as_str().unwrap_or_default())
            .unwrap_or(Value::Null);
        if let Some(due) = schedule["due"]
            .as_str()
            .and_then(|raw| DateTime::parse_from_rfc3339(raw).ok())
        {
            if due <= now {
                pending += 1;
            } else {
                let offset = (due.with_timezone(&Local).date_naive() - now.date_naive()).num_days();
                if (0..7).contains(&offset) {
                    buckets[offset as usize] += 1;
                }
            }
        }
    }
    let forecast: Vec<_> = buckets.iter().enumerate().map(|(i,count)| json!({"date": (now.date_naive()+Days::new(i as u64)).to_string(),"count":count})).collect();
    let mut recall = BTreeMap::<String, (u32, u32)>::new();
    let recall_dates = dates(now.date_naive(), 7)?;
    for event in query(&conn, "SELECT after_json FROM audit WHERE entity='review_cards' AND action='revisar' AND json_valid(after_json)", [])? {
        if event["area"] != "Medicina" { continue; }
        let Some(raw) = event["review_log"].as_str() else { continue; };
        let Ok(log) = serde_json::from_str::<Value>(raw) else { continue; };
        let Some(instant) = log["review_datetime"].as_str().and_then(|value| DateTime::parse_from_rfc3339(value).ok()) else { continue; };
        let day = instant.with_timezone(&Local).date_naive().to_string();
        if instant <= now && recall_dates.contains(&day) {
            let counts = recall.entry(day).or_default();
            counts.0 += u32::from(matches!(log["rating"].as_u64(), Some(2..=4)));
            counts.1 += 1;
        }
    }
    let recall: Vec<_> = recall
        .into_iter()
        .map(|(day, (good, total))| json!([day, 100.0 * f64::from(good) / f64::from(total)]))
        .collect();
    let focus_sql = "SELECT json_array(date,sum(duration_min)) FROM study WHERE deleted_at IS NULL
        AND date BETWEEN ?1 AND ?2 AND source=?3 GROUP BY date ORDER BY date";
    let pomodoro = query(&conn, focus_sql, params![start, day, "Pomodoro"])?;
    let flowtime = query(&conn, focus_sql, params![start, day, "Flowtime"])?;
    let total = |points: &[Value]| {
        points
            .iter()
            .find(|row| row[0] == day)
            .map(|row| row[1].clone())
            .unwrap_or(Value::Null)
    };
    Ok(
        json!({"dates":dates(selected,days)?, "series":{"study":study_points,"exercise":exercise,"sleep":sleep,"weight":weight},
        "agenda":agenda,"studyRecords":study,"tasks":tasks,"habits":habits,"focus":{"Pomodoro":pomodoro,"Flowtime":flowtime},"recall":recall,
        "forecast":{"pending":pending,"days":forecast},
        "today":{"study":total(&study_points),"exercise":total(&exercise),"sleep":total(&sleep),"pending":pending}}),
    )
}

fn dates(end: NaiveDate, count: u32) -> Result<Vec<String>, String> {
    (0..count)
        .rev()
        .map(|offset| {
            end.checked_sub_days(Days::new(offset.into()))
                .map(|day| day.to_string())
                .ok_or_else(|| "Período inválido.".into())
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_fixture_without_creating_or_changing_legacy_database() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("diolino.sqlite3");
        assert!(read(&path, "2026-11-26", 7, None, None).is_err());
        assert!(!path.exists());
        let conn = Connection::open(&path).unwrap();
        assert!(read(&path, "2026-11-26", 7, None, None).is_err());
        conn.execute_batch(
            "PRAGMA user_version=8;
             CREATE TABLE agenda(id,date,time,title,state,duration_min,deleted_at);
             CREATE TABLE study(id,date,time,topic,duration_min,format,source,learning,notes,deleted_at);
             CREATE TABLE plans(id,title,status,deleted_at);
             CREATE TABLE plan_steps(id,plan_id,title,state,priority,due_date,position,deleted_at);
             CREATE TABLE workout(date,duration_min,deleted_at);
             CREATE TABLE sleep(date,start,end,awake_min,deleted_at);
             CREATE TABLE body(id,date,time,weight_kg,deleted_at);
             CREATE TABLE audit(entity,action,after_json);
             CREATE TABLE preferences(key,value);
             INSERT INTO agenda VALUES(1,'2026-11-28','09:00','Consulta','Pendente',20,NULL);
             INSERT INTO study VALUES(1,'2026-11-26','08:00','Medicina',45,'Leitura','Pomodoro',NULL,NULL,NULL);
             INSERT INTO plans VALUES(1,'Plano','Ativo',NULL);
             INSERT INTO plan_steps VALUES(1,1,'Etapa','A fazer','Normal',NULL,1,NULL);
             INSERT INTO workout VALUES('2026-11-26',40,NULL);
             INSERT INTO sleep VALUES('2026-11-26','2026-11-25 23:00','2026-11-26 07:00',30,NULL);
             INSERT INTO body VALUES(1,'2026-11-26','08:00',70,NULL);",
        ).unwrap();
        for (key, value) in [
            ("habit_goal:h:2026-11-20", json!({"name":"Caminhar"})),
            ("habit_day:h:2026-11-26", json!(true)),
            (
                "review_card:x",
                json!({"area":"Medicina","schedule":"{\"due\":\"2000-01-01T00:00:00+00:00\"}"}),
            ),
        ] {
            conn.execute(
                "INSERT INTO preferences VALUES(?1,?2)",
                params![key, value.to_string()],
            )
            .unwrap();
        }
        drop(conn);
        let bytes = std::fs::read(&path).unwrap();
        let data = read(
            &path,
            "2026-11-26",
            7,
            Some("2026-11-26"),
            Some("2026-11-29"),
        )
        .unwrap();
        assert_eq!(data["agenda"][0]["title"], "Consulta");
        assert_eq!(data["tasks"][0]["title"], "Etapa");
        assert_eq!(data["habits"][0]["cells"][29][1], "done");
        assert_eq!(data["today"]["study"], 45);
        assert_eq!(data["today"]["exercise"], 40);
        assert_eq!(data["today"]["sleep"], 7.5);
        assert_eq!(data["today"]["pending"], 1);
        assert_eq!(data["series"]["weight"][0][1], 70);
        assert_eq!(std::fs::read(&path).unwrap(), bytes);
    }
}
