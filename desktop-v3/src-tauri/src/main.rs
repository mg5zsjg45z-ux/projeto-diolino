#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
#[tauri::command]
async fn read_dashboard(day: String, days: u32) -> Result<serde_json::Value,String> {
    if ![7,30,90].contains(&days) || day.len()!=10 ||
       !day.bytes().all(|c| c.is_ascii_digit() || c==b'-') {
        return Err("Período inválido.".into());
    }
    // Development only. No shell or renderer-controlled executable/path.
    // Packaged sidecar is a separate milestone.
    #[cfg(not(debug_assertions))]
    { return Err("A integração de produção ainda não foi habilitada.".into()); }
    #[cfg(debug_assertions)]
    {
        tauri::async_runtime::spawn_blocking(move || {
            let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
            let python = if cfg!(windows) { root.join(".venv/Scripts/python.exe") }
                         else { root.join(".venv/bin/python") };
            let output = std::process::Command::new(python)
                .arg(root.join("desktop-v3/bridge.py")).arg(day).arg(days.to_string())
                .current_dir(&root).env("PYTHONUTF8","1")
                .output().map_err(|_| "Ambiente Python local indisponível.".to_string())?;
            if !output.status.success() {
                return Err("Não foi possível ler o banco local compatível. Confira o ambiente Python.".into());
            }
            serde_json::from_slice(&output.stdout).map_err(|_| "Resposta local inválida.".into())
        }).await.map_err(|_| "Falha de comunicação local.".to_string())?
    }
}
#[tauri::command]
async fn read_study_document(path: String) -> Result<Vec<u8>, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let file = std::path::PathBuf::from(path);
        let extension = file.extension().and_then(|value| value.to_str()).unwrap_or("").to_ascii_lowercase();
        if !["pdf", "txt", "doc", "docx"].contains(&extension.as_str()) {
            return Err("Formato não permitido para material de estudo.".to_string());
        }
        let metadata = std::fs::metadata(&file).map_err(|_| "Não foi possível acessar o arquivo selecionado.".to_string())?;
        if !metadata.is_file() || metadata.len() > 100 * 1024 * 1024 {
            return Err("O arquivo precisa ter até 100 MB.".to_string());
        }
        std::fs::read(file).map_err(|_| "Não foi possível ler o arquivo selecionado.".to_string())
    }).await.map_err(|_| "Falha ao abrir o material de estudo.".to_string())?
}
fn main() {
    tauri::Builder::default().plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![read_dashboard, read_study_document])
        .run(tauri::generate_context!()).expect("Diolino startup failed");
}
