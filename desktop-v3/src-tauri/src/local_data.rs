use rusqlite::{params, Connection, TransactionBehavior};
use serde_json::Value;
use tauri::Manager;

fn section(app: &tauri::AppHandle, key: &str) -> Result<Connection, String> {
    if !SECTION_KEYS.contains(&key) {
        return Err("Seção local inválida.".into());
    }
    open_database(app)
}

pub(crate) const SECTION_KEYS: &[&str] = &[
    WORKSPACE_KEY,
    "diolino-health-entries",
    "diolino-health-goals",
    "diolino-habits-v1",
    "diolino-habit-marks-v1",
    "diolino-preview-reviews",
    "diolino-bible-days",
    "diolino-bible-notes",
    "diolino-food-entries",
    "diolino-food-goals",
    "diolino-food-date-goals",
    "diolino-strength-plan",
    "diolino-daily-tasks",
];

pub(crate) fn open_database(app: &tauri::AppHandle) -> Result<Connection, String> {
    let directory = app
        .path()
        .app_data_dir()
        .map_err(|_| "Pasta de dados 3.0 indisponível.")?;
    std::fs::create_dir_all(&directory)
        .map_err(|_| "Não foi possível criar a pasta de dados 3.0.")?;
    let mut conn = Connection::open(directory.join("desktop-v3.sqlite3"))
        .map_err(|_| "Banco 3.0 indisponível.")?;
    conn.busy_timeout(std::time::Duration::from_secs(3))
        .map_err(|_| "Banco 3.0 ocupado.")?;
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS sections (key TEXT PRIMARY KEY, value TEXT NOT NULL);",
    )
    .map_err(|_| "Não foi possível abrir a estrutura do banco 3.0.")?;
    purge_obsolete_demo_data(&mut conn)?;
    Ok(conn)
}

fn purge_obsolete_demo_data(conn: &mut Connection) -> Result<(), String> {
    use rusqlite::OptionalExtension;
    let tx = conn
        .transaction_with_behavior(TransactionBehavior::Immediate)
        .map_err(|_| "Banco 3.0 ocupado.")?;
    tx.execute(
        "DELETE FROM sections WHERE key IN ('diolino-demo-health-entries','diolino-demo-health-goals')",
        [],
    )
    .map_err(|_| "Não foi possível remover os dados de demonstração.")?;
    let raw: Option<String> = tx
        .query_row(
            "SELECT value FROM sections WHERE key='diolino-health-entries'",
            [],
            |row| row.get(0),
        )
        .optional()
        .map_err(|_| "Não foi possível verificar os registros de saúde.")?;
    if let Some(raw) = raw {
        if let Ok(Value::Array(mut entries)) = serde_json::from_str::<Value>(&raw) {
            let before = entries.len();
            entries.retain(|entry| {
                entry.get("source").and_then(Value::as_str) != Some("Demonstração")
            });
            if entries.len() != before {
                tx.execute(
                    "UPDATE sections SET value=?1 WHERE key='diolino-health-entries'",
                    [Value::Array(entries).to_string()],
                )
                .map_err(|_| "Não foi possível limpar registros de demonstração.")?;
            }
        }
    }
    tx.commit()
        .map_err(|_| "Não foi possível confirmar a limpeza dos dados de demonstração.".into())
}

fn write_section(
    conn: &mut Connection,
    key: &str,
    expected: Option<Value>,
    value: &Value,
) -> Result<(), String> {
    use rusqlite::OptionalExtension;
    let raw = value.to_string();
    if raw.len() > 8 * 1024 * 1024 {
        return Err("Registro excede o limite local.".into());
    }
    let tx = conn
        .transaction_with_behavior(TransactionBehavior::Immediate)
        .map_err(|_| "Banco 3.0 ocupado. Tente novamente.")?;
    let stored: Option<String> = tx
        .query_row("SELECT value FROM sections WHERE key=?1", [key], |row| {
            row.get(0)
        })
        .optional()
        .map_err(|_| "Não foi possível ler a versão dos registros.")?;
    let current = stored
        .map(|raw| serde_json::from_str::<Value>(&raw))
        .transpose()
        .map_err(|_| "Registros da 3.0 inválidos.")?;
    if current != expected {
        return Err(
            "Conflito: outra janela alterou estes dados. Atualize a tela antes de salvar.".into(),
        );
    }
    tx.execute("INSERT INTO sections (key,value) VALUES (?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value",params![key,raw]).map_err(|_|"Não foi possível salvar no banco 3.0.")?;
    tx.commit()
        .map_err(|_| "Não foi possível confirmar a gravação.".into())
}

#[tauri::command]
pub async fn read_local_section(
    app: tauri::AppHandle,
    key: String,
) -> Result<Option<Value>, String> {
    tauri::async_runtime::spawn_blocking(move || {
        use rusqlite::OptionalExtension;
        let raw: Option<String> = section(&app, &key)?
            .query_row("SELECT value FROM sections WHERE key=?1", [&key], |row| {
                row.get(0)
            })
            .optional()
            .map_err(|_| "Não foi possível ler os dados 3.0.")?;
        raw.map(|data| serde_json::from_str(&data).map_err(|_| "Dados 3.0 inválidos.".into()))
            .transpose()
    })
    .await
    .map_err(|_| "Falha de comunicação local.".to_string())?
}

#[tauri::command]
pub async fn write_local_section(
    app: tauri::AppHandle,
    key: String,
    expected: Option<Value>,
    value: Value,
) -> Result<(), String> {
    write_local_section_cas(app, key, expected, value).await
}

#[tauri::command]
pub async fn write_local_section_cas(
    app: tauri::AppHandle,
    key: String,
    expected: Option<Value>,
    value: Value,
) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        if key == WORKSPACE_KEY {
            return Err("Use a gravação transacional dos registros.".into());
        }
        let mut conn = section(&app, &key)?;
        write_section(&mut conn, &key, expected, &value)
    })
    .await
    .map_err(|_| "Falha de comunicação local.".to_string())?
}

pub(crate) const WORKSPACE_KEY: &str = "diolino-workspace-v1";

#[tauri::command]
pub async fn save_workspace(
    app: tauri::AppHandle,
    expected: Option<Value>,
    value: Value,
) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        use rusqlite::{OptionalExtension, TransactionBehavior};
        let raw = value.to_string();
        if raw.len() > 8 * 1024 * 1024 {
            return Err("A base de agenda, planos e estudos atingiu o limite desta prévia.".into());
        }
        let mut conn = section(&app, WORKSPACE_KEY)?;
        let tx = conn
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(|_| "Banco 3.0 ocupado. Tente novamente.")?;
        let stored: Option<String> = tx
            .query_row("SELECT value FROM sections WHERE key=?1", [WORKSPACE_KEY], |row| row.get(0))
            .optional()
            .map_err(|_| "Não foi possível ler a versão dos registros.")?;
        let current = stored
            .map(|raw| serde_json::from_str::<Value>(&raw))
            .transpose()
            .map_err(|_| "Registros da 3.0 inválidos.")?;
        if current != expected {
            return Err("Os registros mudaram em outra janela. Use Atualizar antes de salvar.".into());
        }
        tx.execute(
            "INSERT INTO sections (key,value) VALUES (?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            params![WORKSPACE_KEY, raw],
        )
        .map_err(|_| "Não foi possível guardar os registros.")?;
        tx.commit().map_err(|_| "Não foi possível confirmar a gravação.".into())
    })
    .await
    .map_err(|_| "Falha de comunicação local.".to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn two_database_connections_reject_stale_overwrite() {
        let file = tempfile::NamedTempFile::new().unwrap();
        let mut first = Connection::open(file.path()).unwrap();
        let mut second = Connection::open(file.path()).unwrap();
        first
            .execute_batch("CREATE TABLE sections (key TEXT PRIMARY KEY,value TEXT NOT NULL);")
            .unwrap();
        let initial = serde_json::json!([{"id":"initial"}]);
        write_section(&mut first, "diolino-daily-tasks", None, &initial).unwrap();
        let one = serde_json::json!([{"id":"initial"},{"id":"from-first"}]);
        write_section(&mut first, "diolino-daily-tasks", Some(initial.clone()), &one).unwrap();
        let two = serde_json::json!([{"id":"initial"},{"id":"from-second"}]);
        assert!(
            write_section(&mut second, "diolino-daily-tasks", Some(initial), &two)
                .unwrap_err()
                .contains("Conflito")
        );
        let saved: String = first
            .query_row(
                "SELECT value FROM sections WHERE key='diolino-daily-tasks'",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert!(saved.contains("from-first"));
        assert!(!saved.contains("from-second"));
    }
    #[test]
    fn removes_demo_only_sections_and_rows_from_synthetic_profile() {
        let file = tempfile::NamedTempFile::new().unwrap();
        let mut first = Connection::open(file.path()).unwrap();
        first
            .execute_batch("CREATE TABLE sections (key TEXT PRIMARY KEY,value TEXT NOT NULL);")
            .unwrap();
        let personal =
            serde_json::json!([{"id":1,"activity":"Caminhada","source":"Meus registros"}]);
        let demo =
            serde_json::json!([{"id":2,"activity":"Exercício de exemplo","source":"Demonstração"}]);
        write_section(&mut first, "diolino-health-entries", None, &personal).unwrap();
        write_section(&mut first, "diolino-demo-health-entries", None, &demo).unwrap();
        write_section(
            &mut first,
            "diolino-demo-health-goals",
            None,
            &serde_json::json!({"exerciseMin":30}),
        )
        .unwrap();
        let mut combined = personal.as_array().unwrap().clone();
        combined.extend(demo.as_array().unwrap().clone());
        write_section(
            &mut first,
            "diolino-health-entries",
            Some(personal.clone()),
            &Value::Array(combined),
        )
        .unwrap();
        purge_obsolete_demo_data(&mut first).unwrap();
        drop(first);

        let reopened = Connection::open(file.path()).unwrap();
        let personal_saved: String = reopened
            .query_row(
                "SELECT value FROM sections WHERE key='diolino-health-entries'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        let entries: Value = serde_json::from_str(&personal_saved).unwrap();
        assert_eq!(entries.as_array().unwrap().len(), 1);
        assert_eq!(entries[0]["id"], 1);
        let obsolete_count: i64 = reopened
            .query_row(
                "SELECT count(*) FROM sections WHERE key LIKE 'diolino-demo-%'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(obsolete_count, 0);
        let still_personal: String = reopened
            .query_row(
                "SELECT value FROM sections WHERE key='diolino-health-entries'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(still_personal, personal_saved);
    }
}
