#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
mod backup;
mod local_data;
#[tauri::command]
async fn run_library_cli(tool: String, path: String) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let file = std::path::PathBuf::from(path);
        if !file.is_file() {
            return Err("O arquivo anexado não está acessível.".to_string());
        }
        let ext = file
            .extension()
            .and_then(|x| x.to_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        let (product, exe, args): (&str, &str, Vec<String>) = match (tool.as_str(), ext.as_str()) {
            ("wordcraft", "docx" | "doc" | "txt" | "odt" | "rtf" | "md") => (
                "WordCraft",
                "wordcraft-cli.exe",
                vec!["text".into(), file.to_string_lossy().into_owned()],
            ),
            ("pdfcraft", "pdf") => (
                "PdfCraft",
                "pdfcraft-cli.exe",
                vec!["text".into(), file.to_string_lossy().into_owned()],
            ),
            ("gridcraft", "xlsx" | "xls" | "csv" | "tsv" | "ods") => (
                "GridCraft",
                "gridcraft-cli.exe",
                vec![
                    "cat".into(),
                    file.to_string_lossy().into_owned(),
                    "--range".into(),
                    "A1:Z30".into(),
                ],
            ),
            _ => return Err("Esta ferramenta não oferece leitura para esse formato.".to_string()),
        };
        let mut candidates = Vec::new();
        if let Some(local) = std::env::var_os("LOCALAPPDATA") {
            candidates.push(
                std::path::PathBuf::from(local)
                    .join("Programs/ArtCraft")
                    .join(product)
                    .join(exe),
            );
        }
        if let Some(program_files) = std::env::var_os("ProgramFiles") {
            candidates.push(
                std::path::PathBuf::from(program_files)
                    .join("ArtCraft")
                    .join(product)
                    .join(exe),
            );
        }
        if let Some(program_files_x86) = std::env::var_os("ProgramFiles(x86)") {
            candidates.push(
                std::path::PathBuf::from(program_files_x86)
                    .join("ArtCraft")
                    .join(product)
                    .join(exe),
            );
        }
        let executable = candidates
            .into_iter()
            .find(|candidate| candidate.is_file())
            .ok_or_else(|| {
                format!("CLI do {product} não encontrado. Instale o CLI oficial e tente novamente.")
            })?;
        let output = std::process::Command::new(executable)
            .args(args)
            .output()
            .map_err(|_| format!("Não foi possível iniciar o CLI do {product}."))?;
        if !output.status.success() {
            return Err(String::from_utf8_lossy(&output.stderr).trim().to_string());
        }
        Ok(String::from_utf8_lossy(&output.stdout).into_owned())
    })
    .await
    .map_err(|_| "Falha ao executar a ferramenta de estudo.".to_string())?
}
#[tauri::command]
async fn open_library_document(path: String) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        let file = std::path::PathBuf::from(path);
        if !file.is_file() {
            return Err("O arquivo anexado não está acessível.".to_string());
        }
        let ext = file
            .extension()
            .and_then(|x| x.to_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        if ![
            "pdf", "txt", "doc", "docx", "odt", "rtf", "md", "xlsx", "xls", "csv", "tsv", "ods",
        ]
        .contains(&ext.as_str())
        {
            return Err(
                "Este tipo de arquivo não pode ser aberto como material de estudo.".to_string(),
            );
        }
        #[cfg(target_os = "windows")]
        let mut command = {
            let mut cmd = std::process::Command::new("explorer.exe");
            cmd.arg(&file);
            cmd
        };
        #[cfg(target_os = "macos")]
        let mut command = {
            let mut cmd = std::process::Command::new("open");
            cmd.arg(&file);
            cmd
        };
        #[cfg(all(unix, not(target_os = "macos")))]
        let mut command = {
            let mut cmd = std::process::Command::new("xdg-open");
            cmd.arg(&file);
            cmd
        };
        command.spawn().map(|_| ()).map_err(|_| {
            "Não foi possível abrir o documento no aplicativo padrão do sistema.".to_string()
        })
    })
    .await
    .map_err(|_| "Falha ao abrir o documento.".to_string())?
}
fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            local_data::read_local_section,
            local_data::write_local_section,
            local_data::save_workspace,
            backup::export_backup,
            backup::inspect_backup,
            backup::restore_backup,
            run_library_cli,
            open_library_document
        ])
        .run(tauri::generate_context!())
        .expect("Diolino startup failed");
}
