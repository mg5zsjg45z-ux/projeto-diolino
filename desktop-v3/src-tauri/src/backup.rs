use crate::local_data::{open_database, SECTION_KEYS, WORKSPACE_KEY};
use rusqlite::{params, Connection, TransactionBehavior};
use serde_json::{json, Map, Value};
use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
};
use tauri::Manager;

const FORMAT: &str = "diolino-desktop-v3";
const MAX_BYTES: usize = 128 * 1024 * 1024;
const MAX_SECTION_BYTES: usize = 8 * 1024 * 1024;
const PREFERENCES: &[&str] = &[
    "diolino-theme",
    "diolino-library",
    "diolino-focus-settings",
    "diolino-focus-timer",
    "diolino-focus-sessions",
];
const PENDING_KEY: &str = "__pending";

fn is_date(value: &Value) -> bool {
    value
        .as_str()
        .is_some_and(|text| chrono::NaiveDate::parse_from_str(text, "%Y-%m-%d").is_ok())
}

fn is_time(value: &Value) -> bool {
    value.is_null()
        || value
            .as_str()
            .is_some_and(|text| chrono::NaiveTime::parse_from_str(text, "%H:%M").is_ok())
}

fn optional_string(value: &Value) -> bool {
    value.is_null() || value.is_string()
}

fn optional_number(value: &Value) -> bool {
    value.is_null() || value.is_number()
}

fn valid_agenda(row: &Value) -> bool {
    row["id"].as_i64().is_some()
        && is_date(&row["date"])
        && is_time(&row["time"])
        && row["title"].is_string()
        && optional_number(&row["duration_min"])
        && row["state"].is_string()
}

fn valid_study(row: &Value) -> bool {
    row["id"].as_i64().is_some()
        && is_date(&row["date"])
        && is_time(&row["time"])
        && row["topic"].is_string()
        && row["duration_min"].is_number()
        && row["format"].is_string()
        && optional_string(&row["source"])
        && optional_string(&row["learning"])
        && optional_string(&row["notes"])
        && optional_string(&row["attachment_path"])
        && optional_string(&row["attachment_name"])
}

fn valid_goals(value: &Value) -> bool {
    value
        .as_object()
        .is_some_and(|fields| fields.values().all(Value::is_number))
}

fn valid_focus_session(s: &Value) -> bool {
    s["id"].is_string()
        && matches!(s["mode"].as_str(), Some("Pomodoro" | "Flowtime" | "Livre"))
        && matches!(
            s["status"].as_str(),
            Some("running" | "paused" | "review" | "completed" | "discarded")
        )
        && optional_number(&s["task_id"])
        && optional_string(&s["task_title"])
        && optional_number(&s["planned_seconds"])
        && s["started_at"].as_u64().is_some()
        && optional_number(&s["ended_at"])
        && s["owner"].is_string()
        && s["checkpoint"].as_u64().is_some()
        && s["active_seconds"].as_u64().is_some()
        && s["active_ms"].as_u64().is_some()
        && s["days"].as_object().is_some_and(|days| {
            days.iter().all(|(day, ms)| {
                chrono::NaiveDate::parse_from_str(day, "%Y-%m-%d").is_ok() && ms.as_u64().is_some()
            })
        })
        && s["events"].as_array().is_some_and(|events| {
            events
                .iter()
                .all(|event| event["name"].is_string() && event["at"].as_u64().is_some())
        })
}

fn section_is_valid(key: &str, value: &Value) -> bool {
    match key {
        WORKSPACE_KEY => {
            let agenda = value["agenda"]
                .as_array()
                .is_some_and(|rows| rows.iter().all(valid_agenda));
            let tasks = value["tasks"].as_array().is_some_and(|rows| {
                rows.iter().all(|row| {
                    row["id"].as_i64().is_some()
                        && row["title"].is_string()
                        && row["plan"].is_string()
                        && row["state"].is_string()
                        && row["priority"].is_string()
                        && optional_string(&row["due"])
                })
            });
            let studies = value["studies"]
                .as_array()
                .is_some_and(|rows| rows.iter().all(valid_study));
            let reviews = value["reviews"].as_array().is_some_and(|rows| {
                rows.iter()
                    .all(|row| valid_agenda(row) && row.get("sourceStudy").is_none_or(valid_study))
            });
            let focus =
                value["activeFocus"].is_null() || valid_focus_session(&value["activeFocus"]);
            let history = value.get("focusSessions").is_none_or(|sessions| {
                sessions
                    .as_array()
                    .is_some_and(|rows| rows.iter().all(valid_focus_session))
            });
            agenda && tasks && studies && reviews && focus && history
        }
        "diolino-health-entries" => value.as_array().is_some_and(|rows| {
            rows.iter().all(|row| {
                row["id"].as_i64().is_some()
                    && is_date(&row["date"])
                    && optional_string(&row["activity"])
                    && optional_number(&row["exerciseMin"])
                    && optional_number(&row["sleepHours"])
                    && optional_number(&row["weightKg"])
                    && optional_string(&row["notes"])
                    && row
                        .get("source")
                        .is_none_or(|source| source.as_str() == Some("Meus registros"))
            })
        }),
        "diolino-health-goals" => value.as_object().is_some_and(|fields| {
            fields
                .keys()
                .all(|key| matches!(key.as_str(), "exerciseMin" | "sleepHours"))
                && optional_number(&value["exerciseMin"])
                && optional_number(&value["sleepHours"])
        }),
        "diolino-habit-marks-v1" => value.as_object().is_some_and(|marks| {
            marks.values().all(|days| {
                days.as_object().is_some_and(|dates| {
                    dates.iter().all(|(date, mark)| {
                        chrono::NaiveDate::parse_from_str(date, "%Y-%m-%d").is_ok()
                            && matches!(mark.as_str(), Some("done" | "missed" | "skipped"))
                    })
                })
            })
        }),
        "diolino-habits-v1" => value.as_array().is_some_and(|rows| {
            rows.iter().all(|row| {
                row["id"].is_string()
                    && row["name"]
                        .as_str()
                        .is_some_and(|text| !text.trim().is_empty())
                    && row["description"].is_string()
                    && matches!(
                        row["frequency"].as_str(),
                        Some("daily" | "weekdays" | "weekends")
                    )
                    && is_date(&row["createdAt"])
            })
        }),
        "diolino-preview-reviews" => value.as_array().is_some_and(|rows| {
            rows.iter()
                .all(|row| valid_agenda(row) && row.get("sourceStudy").is_none_or(valid_study))
        }),
        "diolino-caderno" => value["draft"].is_string()
            && value["entries"].as_array().is_some_and(|rows| {
                rows.iter().all(|row| {
                    row["id"].is_string()
                        && row["text"].as_str().is_some_and(|text| !text.trim().is_empty())
                })
            }),
        "diolino-bible-days" => value
            .as_array()
            .is_some_and(|rows| rows.iter().all(is_date)),
        "diolino-bible-notes" => value.as_array().is_some_and(|rows| {
            rows.iter().all(|row| {
                matches!(row["edition"].as_str(), Some("BPM" | "BLIVRE" | "BLT"))
                    && ["book", "bookName", "chapter", "verse", "comment"]
                        .iter()
                        .all(|field| row[*field].is_string())
                    && row["marked"].is_boolean()
            })
        }),
        "diolino-food-entries" => value.as_array().is_some_and(|rows| {
            rows.iter().all(|row| {
                row["id"].is_string()
                    && is_date(&row["date"])
                    && row["code"].as_i64().is_some()
                    && row["name"].is_string()
                    && row["grams"].as_f64().is_some_and(|grams| grams > 0.0)
                    && row["values"]
                        .as_object()
                        .is_some_and(|values| values.values().all(Value::is_number))
            })
        }),
        "diolino-food-goals" => valid_goals(value),
        "diolino-food-date-goals" => value.as_object().is_some_and(|days| {
            days.iter().all(|(date, goals)| {
                chrono::NaiveDate::parse_from_str(date, "%Y-%m-%d").is_ok() && valid_goals(goals)
            })
        }),
        "diolino-strength-plan" => value.as_array().is_some_and(|rows| {
            rows.iter().all(|row| {
                row["id"].is_string()
                    && is_date(&row["date"])
                    && row["name"].is_string()
                    && row["sets"].as_i64().is_some_and(|sets| sets > 0)
                    && row["reps"].is_string()
                    && (row["load"].is_null()
                        || row["load"].as_f64().is_some_and(|load| load >= 0.0))
                    && row["notes"].is_string()
            })
        }),
        "diolino-daily-tasks" => value.as_array().is_some_and(|rows| {
            rows.iter().all(|row| {
                row["id"].is_string()
                    && is_date(&row["date"])
                    && row["text"].is_string()
                    && row["done"].is_boolean()
                    && optional_number(&row["minutes"])
                    && row["steps"].as_array().is_some_and(|steps| {
                        steps.iter().all(|step| {
                            step["id"].is_string()
                                && step["text"].is_string()
                                && step["done"].is_boolean()
                        })
                    })
            })
        }),
        _ => false,
    }
}

fn validate(value: &Value) -> Result<(), String> {
    if value["format"] != FORMAT || value["version"].as_u64() != Some(1) {
        return Err("Arquivo incompatível. Escolha um backup da versão 3.0.".into());
    }
    if !value["createdAt"]
        .as_str()
        .is_some_and(|text| chrono::DateTime::parse_from_rfc3339(text).is_ok())
    {
        return Err("Data do backup inválida.".into());
    }
    let sections = value["sections"]
        .as_object()
        .ok_or("Seções do backup inválidas.")?;
    for (key, data) in sections {
        if !SECTION_KEYS.contains(&key.as_str())
            || !section_is_valid(key, data)
            || data.to_string().len() > MAX_SECTION_BYTES
        {
            return Err(format!("Seção inválida no backup: {key}."));
        }
    }
    let preferences = value["preferences"]
        .as_object()
        .ok_or("Preferências do backup inválidas.")?;
    for (key, data) in preferences {
        let valid = match key.as_str() {
            "diolino-theme" => matches!(data.as_str(), Some("paper" | "xp" | "classic" | "royale")),
            "diolino-library" => data.as_array().is_some_and(|rows| {
                rows.iter().all(|row| {
                    ["id", "name", "path"]
                        .iter()
                        .all(|field| row[*field].is_string())
                })
            }),
            "diolino-focus-settings" => data.as_object().is_some_and(|settings| {
                [
                    "focusMin",
                    "shortBreakMin",
                    "longBreakMin",
                    "longBreakEvery",
                ]
                .iter()
                .all(|field| data[*field].as_u64().is_some())
                    && settings.keys().all(|key| {
                        matches!(
                            key.as_str(),
                            "focusMin" | "shortBreakMin" | "longBreakMin" | "longBreakEvery"
                        )
                    })
            }),
            "diolino-focus-timer" => data.as_object().is_some_and(|clock| {
                matches!(
                    data["phase"].as_str(),
                    Some("focus" | "shortBreak" | "longBreak")
                ) && data["remainingMs"].as_u64().is_some()
                    && data["running"].is_boolean()
                    && optional_number(&data["endsAt"])
                    && data["cycles"].as_u64().is_some()
                    && data.get("task").is_none_or(|task| {
                        task["title"].is_string() && task["minutes"].as_u64().is_some()
                    })
                    && data.get("sessionId").is_none_or(optional_string)
                    && data.get("startedAt").is_none_or(optional_number)
                    && data
                        .get("activeSeconds")
                        .is_none_or(|seconds| seconds.as_u64().is_some())
                    && data.get("recovered").is_none_or(Value::is_boolean)
                    && clock.keys().all(|key| {
                        matches!(
                            key.as_str(),
                            "phase"
                                | "remainingMs"
                                | "running"
                                | "endsAt"
                                | "cycles"
                                | "task"
                                | "sessionId"
                                | "startedAt"
                                | "activeSeconds"
                                | "recovered"
                        )
                    })
            }),
            "diolino-focus-sessions" => data.as_array().is_some_and(|rows| {
                rows.iter().all(|row| {
                    row["id"].is_string()
                        && is_date(&row["date"])
                        && row["minutes"].as_u64().is_some()
                        && row["completedAt"].as_u64().is_some()
                })
            }),
            _ => false,
        };
        if !PREFERENCES.contains(&key.as_str())
            || !valid
            || data.to_string().len() > MAX_SECTION_BYTES
        {
            return Err(format!("Preferência inválida no backup: {key}."));
        }
    }
    Ok(())
}

fn check_path(path: &Path) -> Result<(), String> {
    if path
        .file_name()
        .and_then(|name| name.to_str())
        .is_some_and(|name| name.to_ascii_lowercase().ends_with(".diolino-backup.json"))
    {
        Ok(())
    } else {
        Err("Use um arquivo terminado em .diolino-backup.json.".into())
    }
}

fn discard_obsolete_demo_data(value: &mut Value) {
    if let Some(sections) = value.get_mut("sections").and_then(Value::as_object_mut) {
        sections.remove("diolino-demo-health-entries");
        sections.remove("diolino-demo-health-goals");
        if let Some(Value::Array(rows)) = sections.get_mut("diolino-health-entries") {
            rows.retain(|row| row.get("source").and_then(Value::as_str) != Some("Demonstração"));
        }
    }
}

fn read_backup(path: &Path) -> Result<Value, String> {
    check_path(path)?;
    let file = File::open(path).map_err(|_| "Não foi possível abrir o backup.")?;
    if !file
        .metadata()
        .map_err(|_| "Arquivo indisponível.")?
        .is_file()
    {
        return Err("Selecione um arquivo de backup.".into());
    }
    let mut bytes = Vec::new();
    file.take(MAX_BYTES as u64 + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| "Não foi possível ler o backup.")?;
    if bytes.len() > MAX_BYTES {
        return Err("O arquivo excede o limite de backup.".into());
    }
    let mut value: Value =
        serde_json::from_slice(&bytes).map_err(|_| "O arquivo de backup está danificado.")?;
    // Older alpha backups may contain demo buckets; never restore them into a personal profile.
    discard_obsolete_demo_data(&mut value);
    validate(&value)?;
    Ok(value)
}

fn snapshot(conn: &Connection, preferences: Value, web_sections: Value) -> Result<Value, String> {
    let mut statement = conn
        .prepare("SELECT key,value FROM sections")
        .map_err(|_| "Não foi possível consultar os registros locais.")?;
    let mut rows = statement
        .query([])
        .map_err(|_| "Não foi possível ler os registros locais.")?;
    let mut sections = Map::new();
    while let Some(row) = rows
        .next()
        .map_err(|_| "Não foi possível ler a base local.")?
    {
        let key: String = row.get(0).map_err(|_| "Chave local inválida.")?;
        if !SECTION_KEYS.contains(&key.as_str()) {
            return Err("A base contém dados de uma versão incompatível.".into());
        }
        let raw: String = row.get(1).map_err(|_| "Registro local inválido.")?;
        sections.insert(
            key,
            serde_json::from_str(&raw).map_err(|_| "Registro local danificado.")?,
        );
    }
    if let Some(web) = web_sections.as_object() {
        for (key, data) in web {
            if key == PENDING_KEY {
                continue;
            }
            if !SECTION_KEYS.contains(&key.as_str()) || !section_is_valid(key, data) {
                return Err(format!("Seção do armazenamento local inválida: {key}."));
            }
            let pending = web
                .get(PENDING_KEY)
                .and_then(|pending| pending.get(key))
                .and_then(Value::as_bool)
                .unwrap_or(false);
            if !sections.contains_key(key) || pending {
                sections.insert(key.clone(), data.clone());
            }
        }
    } else {
        return Err("Seções locais do WebView inválidas.".into());
    }
    let value = json!({"format": FORMAT, "version": 1, "createdAt": chrono::Utc::now().to_rfc3339(), "sections": sections, "preferences": preferences});
    validate(&value)?;
    Ok(value)
}

fn write_new(path: &Path, value: &Value) -> Result<(), String> {
    check_path(path)?;
    let bytes = serde_json::to_vec(value).map_err(|_| "Não foi possível preparar o backup.")?;
    if bytes.len() > MAX_BYTES {
        return Err("Os dados excedem o limite desta versão de backup.".into());
    }
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .map_err(|_| "Não foi possível criar o arquivo. Se já existir, escolha outro nome.")?;
    let result = file.write_all(&bytes).and_then(|_| file.sync_all());
    drop(file);
    if result.is_err() {
        let _ = fs::remove_file(path);
        return Err("Não foi possível concluir a gravação do backup.".into());
    }
    Ok(())
}

#[tauri::command]
pub async fn export_backup(
    app: tauri::AppHandle,
    path: PathBuf,
    preferences: Value,
    sections: Value,
) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        let conn = open_database(&app)?;
        write_new(&path, &snapshot(&conn, preferences, sections)?)
    })
    .await
    .map_err(|_| "Falha ao exportar o backup.".to_string())?
}

#[tauri::command]
pub async fn inspect_backup(path: PathBuf) -> Result<Value, String> {
    tauri::async_runtime::spawn_blocking(move || read_backup(&path))
        .await
        .map_err(|_| "Falha ao verificar o backup.".to_string())?
}

fn replace(
    conn: &mut Connection,
    backup: &Value,
    preferences: Value,
    web_sections: Value,
    recovery: &Path,
) -> Result<(), String> {
    validate(backup)?;
    let tx = conn
        .transaction_with_behavior(TransactionBehavior::Immediate)
        .map_err(|_| "Banco ocupado. Tente novamente.")?;
    let previous = snapshot(&tx, preferences, web_sections)?;
    write_new(recovery, &previous)?;
    tx.execute("DELETE FROM sections", [])
        .map_err(|_| "Não foi possível preparar a restauração.")?;
    for (key, data) in backup["sections"].as_object().unwrap() {
        tx.execute(
            "INSERT INTO sections (key,value) VALUES (?1,?2)",
            params![key, data.to_string()],
        )
        .map_err(|_| "Não foi possível restaurar os registros.")?;
    }
    tx.commit()
        .map_err(|_| "A restauração não foi confirmada.".into())
}

#[tauri::command]
pub async fn restore_backup(
    app: tauri::AppHandle,
    backup: Value,
    preferences: Value,
    sections: Value,
) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let directory = app
            .path()
            .app_data_dir()
            .map_err(|_| "Pasta de recuperação indisponível.")?
            .join("backups");
        fs::create_dir_all(&directory)
            .map_err(|_| "Não foi possível criar a pasta de recuperação.")?;
        let recovery = directory.join(format!(
            "antes-de-restaurar-{}.diolino-backup.json",
            chrono::Utc::now().format("%Y%m%d-%H%M%S-%f")
        ));
        replace(
            &mut open_database(&app)?,
            &backup,
            preferences,
            sections,
            &recovery,
        )?;
        Ok(recovery.to_string_lossy().into_owned())
    })
    .await
    .map_err(|_| "Falha ao restaurar o backup.".to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn focus_history_and_active_session_survive_workspace_backup() {
        let session = json!({"id":"focus-1","mode":"Flowtime","task_id":4,"task_title":"Ler",
            "planned_seconds":null,"started_at":1000,"ended_at":null,"status":"paused",
            "owner":"tab","checkpoint":6000,"active_seconds":5,"active_ms":5000,
            "days":{"2026-11-26":5000},"events":[{"name":"paused","at":6000}]});
        let workspace = json!({"tasks":[],"studies":[],"agenda":[],"reviews":[],
            "dailyMigration":2,"activeFocus":session,"focusSessions":[]});
        let mut db = Connection::open_in_memory().unwrap();
        db.execute_batch("CREATE TABLE sections (key TEXT PRIMARY KEY, value TEXT NOT NULL);")
            .unwrap();
        let folder = tempfile::tempdir().unwrap();
        let backup = json!({"format":FORMAT,"version":1,"createdAt":"2026-11-26T12:00:00Z",
            "sections":{(WORKSPACE_KEY):workspace},"preferences":{}});
        replace(
            &mut db,
            &backup,
            json!({}),
            json!({}),
            &folder.path().join("recovery.diolino-backup.json"),
        )
        .unwrap();
        assert_eq!(
            snapshot(&db, json!({}), json!({})).unwrap()["sections"][WORKSPACE_KEY],
            workspace
        );
        let mut broken = backup;
        broken["sections"][WORKSPACE_KEY]["activeFocus"]["days"] = json!([]);
        assert!(validate(&broken).is_err());
    }

    #[test]
    fn obsolete_demo_data_is_discarded_from_older_backups() {
        let mut backup = json!({"sections": {
            "diolino-demo-health-entries": [{"id": 2}],
            "diolino-demo-health-goals": {"exerciseMin": 30},
            "diolino-health-entries": [
                {"id": 1, "source": "Meus registros"},
                {"id": 2, "source": "Demonstração"}
            ]
        }});
        discard_obsolete_demo_data(&mut backup);
        assert!(backup["sections"]
            .get("diolino-demo-health-entries")
            .is_none());
        assert!(backup["sections"]
            .get("diolino-demo-health-goals")
            .is_none());
        assert_eq!(
            backup["sections"]["diolino-health-entries"],
            json!([{"id":1,"source":"Meus registros"}])
        );
    }

    #[test]
    fn backup_roundtrip_and_preventive_copy_in_a_new_profile() {
        let folder = tempfile::tempdir().unwrap();
        let exported = folder.path().join("export.diolino-backup.json");
        let recovery = folder.path().join("previous.diolino-backup.json");
        let mut db = Connection::open_in_memory().unwrap();
        db.execute_batch("CREATE TABLE sections (key TEXT PRIMARY KEY, value TEXT NOT NULL);")
            .unwrap();
        let backup = json!({
            "format": FORMAT, "version": 1, "createdAt": "2026-11-26T00:00:00Z",
            "sections": {"diolino-bible-days": ["2026-11-26"]},
            "preferences": {"diolino-theme": "royale"}
        });
        write_new(&exported, &backup).unwrap();
        assert!(write_new(&exported, &backup).is_err());
        let imported = read_backup(&exported).unwrap();
        replace(
            &mut db,
            &imported,
            json!({"diolino-theme":"xp"}),
            json!({}),
            &recovery,
        )
        .unwrap();
        let restored = snapshot(&db, imported["preferences"].clone(), json!({})).unwrap();
        assert_eq!(restored["sections"], backup["sections"]);
        let previous = read_backup(&recovery).unwrap();
        assert_eq!(previous["sections"], json!({}));
        assert_eq!(previous["preferences"]["diolino-theme"], "xp");

        let mut invalid = backup.clone();
        invalid["sections"]["diolino-bible-days"] = json!([17]);
        let rejected = folder.path().join("rejected.diolino-backup.json");
        assert!(replace(&mut db, &invalid, json!({}), json!({}), &rejected).is_err());
        assert!(!rejected.exists());
        assert_eq!(
            snapshot(&db, json!({}), json!({})).unwrap()["sections"],
            backup["sections"]
        );
        assert!(replace(&mut db, &backup, json!({}), json!({}), &recovery).is_err());
        assert_eq!(
            snapshot(&db, json!({}), json!({})).unwrap()["sections"],
            backup["sections"]
        );
        fs::write(&rejected, b"{broken").unwrap();
        assert!(read_backup(&rejected).is_err());
    }

    #[test]
    fn legacy_webview_habits_and_marks_are_in_export_and_pre_restore_copy() {
        let folder = tempfile::tempdir().unwrap();
        let exported = folder.path().join("legacy.diolino-backup.json");
        let recovery = folder.path().join("before.diolino-backup.json");
        let habits = json!([{"id":"old-habit-1","name":"Leitura","description":"","frequency":"daily","createdAt":"2026-11-01"}]);
        let marks = json!({"old-habit-1":{"2026-11-25":"done","2026-11-26":"skipped"}});
        let source = Connection::open_in_memory().unwrap();
        source
            .execute_batch("CREATE TABLE sections (key TEXT PRIMARY KEY, value TEXT NOT NULL);")
            .unwrap();
        let export = snapshot(
            &source,
            json!({}),
            json!({"diolino-habits-v1":habits,"diolino-habit-marks-v1":marks}),
        )
        .unwrap();
        write_new(&exported, &export).unwrap();
        let imported = read_backup(&exported).unwrap();
        let mut empty = Connection::open_in_memory().unwrap();
        empty
            .execute_batch("CREATE TABLE sections (key TEXT PRIMARY KEY, value TEXT NOT NULL);")
            .unwrap();
        let live = json!({"diolino-habits-v1":habits,"diolino-habit-marks-v1":marks,"__pending":{"diolino-habits-v1":false,"diolino-habit-marks-v1":false}});
        replace(&mut empty, &imported, json!({}), live, &recovery).unwrap();
        let restored = snapshot(&empty, json!({}), json!({})).unwrap();
        assert_eq!(
            restored["sections"]["diolino-habits-v1"][0]["id"],
            "old-habit-1"
        );
        assert_eq!(
            restored["sections"]["diolino-habit-marks-v1"]["old-habit-1"]["2026-11-25"],
            "done"
        );
        let previous = read_backup(&recovery).unwrap();
        assert_eq!(
            previous["sections"]["diolino-habits-v1"][0]["name"],
            "Leitura"
        );
        assert_eq!(
            previous["sections"]["diolino-habit-marks-v1"]["old-habit-1"]["2026-11-26"],
            "skipped"
        );
    }

    #[test]
    fn invalid_webview_section_aborts_restore_before_replacing() {
        let folder = tempfile::tempdir().unwrap();
        let recovery = folder.path().join("before.diolino-backup.json");
        let mut db = Connection::open_in_memory().unwrap();
        db.execute_batch("CREATE TABLE sections (key TEXT PRIMARY KEY, value TEXT NOT NULL); INSERT INTO sections VALUES ('diolino-habits-v1','[{\"id\":\"durable\",\"name\":\"SQLite\",\"description\":\"\",\"frequency\":\"daily\",\"createdAt\":\"2026-11-01\"}]');").unwrap();
        let backup = json!({"format":FORMAT,"version":1,"createdAt":"2026-11-26T00:00:00Z","sections":{"diolino-bible-days":["2026-11-26"]},"preferences":{}});
        let err = replace(
            &mut db,
            &backup,
            json!({}),
            json!({"diolino-habits-v1":[{"name":"invalido"}]}),
            &recovery,
        )
        .unwrap_err();
        assert!(err.contains("inválida"));
        assert!(!recovery.exists());
        let kept: String = db
            .query_row(
                "SELECT value FROM sections WHERE key='diolino-habits-v1'",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert!(kept.contains("durable"));
    }

    #[test]
    fn durable_section_wins_stale_webview_but_pending_newer_value_is_reconciled() {
        let db = Connection::open_in_memory().unwrap();
        db.execute_batch("CREATE TABLE sections (key TEXT PRIMARY KEY, value TEXT NOT NULL);")
            .unwrap();
        db.execute("INSERT INTO sections VALUES (?1,?2)",params!["diolino-habits-v1",json!([{"id":"durable","name":"Durável","description":"","frequency":"daily","createdAt":"2026-11-01"}]).to_string()]).unwrap();
        let stale = json!({"diolino-habits-v1":[{"id":"stale","name":"Antigo","description":"","frequency":"daily","createdAt":"2026-11-01"}],"__pending":{"diolino-habits-v1":false}});
        let backup = snapshot(&db, json!({}), stale).unwrap();
        assert_eq!(backup["sections"]["diolino-habits-v1"][0]["id"], "durable");
        let newer = json!({"diolino-habits-v1":[{"id":"newer","name":"Novo","description":"","frequency":"daily","createdAt":"2026-11-01"}],"__pending":{"diolino-habits-v1":true}});
        let backup = snapshot(&db, json!({}), newer).unwrap();
        assert_eq!(backup["sections"]["diolino-habits-v1"][0]["id"], "newer");
    }
    #[test]
    fn backup_validation_rejects_invalid_fields_for_each_migrated_section() {
        assert!(section_is_valid(
            "diolino-health-entries",
            &json!([{"id":7,"date":"2026-11-26","activity":null,"exerciseMin":30,"sleepHours":null,"weightKg":null,"notes":null,"source":"Meus registros"}])
        ));
        assert!(!section_is_valid(
            "diolino-health-entries",
            &json!([{"id":"7","date":"not-a-date","activity":null,"exerciseMin":"30"}])
        ));
        assert!(section_is_valid(
            "diolino-strength-plan",
            &json!([{"id":"lift-1","date":"2026-11-26","name":"Agachamento","sets":3,"reps":"8","load":null,"notes":""}])
        ));
        assert!(!section_is_valid(
            "diolino-strength-plan",
            &json!([{"id":"lift-1","date":"2026-11-26","name":"Agachamento","sets":3,"reps":"8","load":-1,"notes":""}])
        ));
        assert!(section_is_valid(
            "diolino-daily-tasks",
            &json!([{"id":"task-1","date":"2026-11-26","text":"Ler","done":false,"minutes":null,"steps":[]}])
        ));
        assert!(!section_is_valid(
            "diolino-daily-tasks",
            &json!([{"id":"task-1","date":"2026-11-26","text":"Ler","done":"false","steps":[]}])
        ));
    }
}
