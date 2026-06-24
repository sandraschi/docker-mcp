#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend;
use backend::{BackendProcess, materialize_backend};
use std::io::BufRead;
use std::process::{Command, Stdio};
use std::sync::Mutex;
use tauri::{Emitter, Manager};
#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[tauri::command]
async fn start_backend(
    app: tauri::AppHandle,
    state: tauri::State<'_, BackendProcess>,
) -> Result<String, String> {
    let path = materialize_backend(&app)?;
    let mut child = Command::new(&path)
        .env("DOCKER_TAURI", "1")
        .args(["--http", "--port", "10807"])
        .creation_flags(0x0800_0000)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start backend: {e}"))?;

    let stdout = child.stdout.take().ok_or("No stdout")?;
    let stderr = child.stderr.take().ok_or("No stderr")?;
    *state.0.lock().unwrap() = Some(child);

    let ac1 = app.clone();
    let ac2 = app.clone();
    tauri::async_runtime::spawn(async move {
        let reader = std::io::BufReader::new(stdout);
        for line in reader.lines().flatten() {
            if line.contains("Uvicorn running") || line.contains("Application startup complete") {
                let _ = ac1.emit("backend-status", "ready");
                break;
            }
        }
    });
    tauri::async_runtime::spawn(async move {
        let reader = std::io::BufReader::new(stderr);
        for line in reader.lines().flatten() {
            if line.contains("Uvicorn running") || line.contains("Application startup complete") {
                let _ = ac2.emit("backend-status", "ready");
                break;
            }
        }
    });

    Ok("Backend starting on port 10807".into())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(BackendProcess(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![start_backend])
        .setup(|app| {
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                if let Err(e) =
                    start_backend(handle.clone(), handle.state::<BackendProcess>()).await
                {
                    eprintln!("Backend error: {}", e);
                    let _ = handle.emit("backend-status", format!("error: {}", e));
                }
            });
            #[cfg(debug_assertions)]
            if let Some(window) = app.get_webview_window("main") {
                window.open_devtools();
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error building tauri application")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                if let Some(mut child) = app.state::<BackendProcess>().0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        });
}
