fn main() {
    let icon = std::path::PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap())
        .join("icons/icon.ico");
    let windows = tauri_build::WindowsAttributes::new().window_icon_path(icon);
    let attributes = tauri_build::Attributes::new().windows_attributes(windows);
    tauri_build::try_build(attributes).expect("failed to build Tauri application");
}
