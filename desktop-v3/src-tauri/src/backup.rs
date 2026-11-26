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

fn section_is_valid(key: &str, value: &Value) -> bool {
    match key {
        WORKSPACE_KEY => {
            let fields: &[(&str, &[&str])] = &[
                ("agenda", &["title", "date", "state"]),
                ("tasks", &["title", "plan", "state", "priority"]),
                ("studies", &["topic", "date", "format"]),
                ("reviews", &["title", "date", "state"]),
            ];
            fields.iter().all(|(name, strings)| {
                value[*name].as_array().is_some_and(|rows| {
                    rows.iter().all(|row| {
                        row["id"].as_i64().is_some()
                            && strings.iter().all(|field| row[*field].is_string())
                            && (*name != "studies" || row["duration_min"].is_number())
                    })
                })
            })
        }
        "diolino-bible-days" => value
            .as_array()
            .is_some_and(|rows| rows.iter().all(Value::is_string)),
        "diolino-habit-marks-v1"
        | "diolino-health-goals"
        | "diolino-food-goals"
        | "diolino-food-date-goals" => value.is_object(),
        _ => value
            .as_array()
            .is_some_and(|rows| rows.iter().all(Value::is_object)),
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
            "diolino-theme" => matches!(data.as_str(), Some("xp" | "classic" | "royale")),
            "diolino-library" => data.as_array().is_some_and(|rows| {
                rows.iter().all(|row| {
                    ["id", "name", "path"]
                        .iter()
                        .all(|field| row[*field].is_string())
                })
            }),
            "diolino-focus-sessions" => data
                .as_array()
                .is_some_and(|rows| rows.iter().all(Value::is_object)),
            _ => data.is_object(),
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
    let value =
        serde_json::from_slice(&bytes).map_err(|_| "O arquivo de backup está danificado.")?;
    validate(&value)?;
    Ok(value)
}

fn snapshot(conn: &Connection, preferences: Value) -> Result<Value, String> {
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
) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        let conn = open_database(&app)?;
        write_new(&path, &snapshot(&conn, preferences)?)
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
    recovery: &Path,
) -> Result<(), String> {
    validate(backup)?;
    let tx = conn
        .transaction_with_behavior(TransactionBehavior::Immediate)
        .map_err(|_| "Banco ocupado. Tente novamente.")?;
    write_new(recovery, &snapshot(&tx, preferences)?)?;
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
        replace(&mut open_database(&app)?, &backup, preferences, &recovery)?;
        Ok(recovery.to_string_lossy().into_owned())
    })
    .await
    .map_err(|_| "Falha ao restaurar o backup.".to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;

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
        replace(&mut db, &imported, json!({"diolino-theme":"xp"}), &recovery).unwrap();
        let restored = snapshot(&db, imported["preferences"].clone()).unwrap();
        assert_eq!(restored["sections"], backup["sections"]);
        let previous = read_backup(&recovery).unwrap();
        assert_eq!(previous["sections"], json!({}));
        assert_eq!(previous["preferences"]["diolino-theme"], "xp");

        let mut invalid = backup.clone();
        invalid["sections"]["diolino-bible-days"] = json!([17]);
        let rejected = folder.path().join("rejected.diolino-backup.json");
        assert!(replace(&mut db, &invalid, json!({}), &rejected).is_err());
        assert!(!rejected.exists());
        assert_eq!(
            snapshot(&db, json!({})).unwrap()["sections"],
            backup["sections"]
        );
        assert!(replace(&mut db, &backup, json!({}), &recovery).is_err());
        assert_eq!(
            snapshot(&db, json!({})).unwrap()["sections"],
            backup["sections"]
        );
        fs::write(&rejected, b"{broken").unwrap();
        assert!(read_backup(&rejected).is_err());
    }
}
