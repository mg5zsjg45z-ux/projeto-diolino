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
async fn run_study_cli(tool: String, path: String) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let file = std::path::PathBuf::from(path);
        if !file.is_file() { return Err("O arquivo anexado não está acessível.".to_string()); }
        let ext = file.extension().and_then(|x| x.to_str()).unwrap_or("").to_ascii_lowercase();
        let (product, exe, args): (&str, &str, Vec<String>) = match (tool.as_str(), ext.as_str()) {
            ("wordcraft", "docx" | "doc" | "txt" | "odt" | "rtf" | "md") => ("WordCraft", "wordcraft-cli.exe", vec!["text".into(), file.to_string_lossy().into_owned()]),
            ("pdfcraft", "pdf") => ("PdfCraft", "pdfcraft-cli.exe", vec!["text".into(), file.to_string_lossy().into_owned()]),
            ("gridcraft", "xlsx" | "xls" | "csv" | "tsv" | "ods") => ("GridCraft", "gridcraft-cli.exe", vec!["cat".into(), file.to_string_lossy().into_owned(), "--range".into(), "A1:Z30".into()]),
            _ => return Err("Esta ferramenta não oferece leitura para esse formato.".to_string()),
        };
        let mut candidates = Vec::new();
        if let Some(local) = std::env::var_os("LOCALAPPDATA") { candidates.push(std::path::PathBuf::from(local).join("Programs/ArtCraft").join(product).join(exe)); }
        if let Some(program_files) = std::env::var_os("ProgramFiles") { candidates.push(std::path::PathBuf::from(program_files).join("ArtCraft").join(product).join(exe)); }
        if let Some(program_files_x86) = std::env::var_os("ProgramFiles(x86)") { candidates.push(std::path::PathBuf::from(program_files_x86).join("ArtCraft").join(product).join(exe)); }
        let executable = candidates.into_iter().find(|candidate| candidate.is_file()).ok_or_else(|| format!("CLI do {product} não encontrado. Instale o CLI oficial e tente novamente."))?;
        let output = std::process::Command::new(executable).args(args).output().map_err(|_| format!("Não foi possível iniciar o CLI do {product}."))?;
        if !output.status.success() { return Err(String::from_utf8_lossy(&output.stderr).trim().to_string()); }
        Ok(String::from_utf8_lossy(&output.stdout).into_owned())
    }).await.map_err(|_| "Falha ao executar a ferramenta de estudo.".to_string())?
}
fn main() {
    tauri::Builder::default().plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![read_dashboard, run_study_cli])
        .run(tauri::generate_context!()).expect("Diolino startup failed");
}
