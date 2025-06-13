import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import subprocess
import requests # HTTPリクエスト用
import re
import threading # GUIフリーズ対策
import socket # IPアドレス取得用
import json # デバッグ用
import datetime # タイムスタンプはサーバー側で付与するのでクライアントでは不要かも
import os   # ファイルパス操作のためにインポート
import sys  # PyInstallerで実行時のパス取得のため (オプション)

# --- 設定ファイル名 ---
CONFIG_FILE_NAME = "client_config.json"

# --- デフォルト設定 ---
DEFAULT_CONFIG = {
    "server_ip": "192.168.2.123", # デフォルトのサーバーIP
    "server_port": 5000,
    "usbip_cmd": "C:\\02_workspace\\tools\\usbip-win-0.3.6-dev\\usbip.exe", # デフォルトはPATHが通っている前提
    "username": "DefaultUser"
}

# --- グローバル変数 (設定値) ---
# これらは load_config() で初期化される
SERVER_IP = DEFAULT_CONFIG["server_ip"]
SERVER_PORT = DEFAULT_CONFIG["server_port"]
USBIP_CMD = DEFAULT_CONFIG["usbip_cmd"]
username = DEFAULT_CONFIG["username"]
SERVER_URL = f"http://{SERVER_IP}:{SERVER_PORT}" # SERVER_IP, SERVER_PORT 変更時に更新が必要

my_local_ip = "Unknown" # これは設定ファイルには含めない

# --- ヘルパー関数: 設定ファイルのパス取得 ---
def get_config_file_path():
    """設定ファイルのフルパスを取得する"""
    # PyInstallerで --onefile でexe化した場合、sys.executable はexeのパス
    # 開発時はスクリプトのあるディレクトリ
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # PyInstallerでバンドルされた場合 (sys._MEIPASS は一時展開先なので使わない)
        application_path = os.path.dirname(sys.executable)
    else:
        # 通常のPythonスクリプトとして実行された場合
        application_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(application_path, CONFIG_FILE_NAME)

# --- 設定の読み込みと保存 ---
def load_config():
    global SERVER_IP, SERVER_PORT, USBIP_CMD, username, SERVER_URL
    config_path = get_config_file_path()
    config = DEFAULT_CONFIG.copy() # デフォルト値で初期化

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                loaded_settings = json.load(f)
                config.update(loaded_settings) # デフォルト値を上書き
            print(f"Loaded configuration from {config_path}")
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {config_path}. Using default settings.")
        except Exception as e:
            print(f"Error loading config from {config_path}: {e}. Using default settings.")
    else:
        print(f"Configuration file not found at {config_path}. Using default settings and creating one.")
        # ファイルがなければデフォルト設定で保存しておく
        # save_config(config) # ここで保存するか、最初の設定変更時まで待つか

    SERVER_IP = config["server_ip"]
    SERVER_PORT = int(config["server_port"]) # ポートは整数であるべき
    USBIP_CMD = config["usbip_cmd"]
    username = config["username"]
    SERVER_URL = f"http://{SERVER_IP}:{SERVER_PORT}" # SERVER_URLも更新
    
    # GUIのタイトルなども更新するならここ
    if 'root' in globals() and root: # rootウィンドウが既に存在すれば
        update_gui_titles_and_labels()


def save_config(config_data=None):
    """現在の設定を指定されたデータで、またはグローバル変数から保存する"""
    global SERVER_IP, SERVER_PORT, USBIP_CMD, username
    config_path = get_config_file_path()
    
    if config_data: # 引数で設定データが渡された場合
        data_to_save = config_data
    else: # グローバル変数から現在の設定を保存
        data_to_save = {
            "server_ip": SERVER_IP,
            "server_port": SERVER_PORT,
            "usbip_cmd": USBIP_CMD,
            "username": username
        }
        
    try:
        with open(config_path, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        print(f"Configuration saved to {config_path}")
        update_status_bar("Configuration saved.")
    except Exception as e:
        print(f"Error saving config to {config_path}: {e}")
        messagebox.showerror("Config Error", f"Failed to save configuration: {e}")
        update_status_bar(f"Error saving configuration: {e}")

def update_gui_titles_and_labels():
    """GUIのタイトルやラベルを設定値に基づいて更新する"""
    global SERVER_URL
    SERVER_URL = f"http://{SERVER_IP}:{SERVER_PORT}" # SERVER_URLも更新
    if 'root' in globals() and root:
        root.title(f"USB/IP Client GUI - User: {username} (IP: {my_local_ip}) - Server: {SERVER_IP}")
    if 'devices_frame' in globals() and devices_frame:
        devices_frame.config(text=f"USB Devices on Server ({SERVER_IP}:{SERVER_PORT})")
    # 他にも更新が必要なラベルがあればここに追加


# --- 設定変更ダイアログ ---
class SettingsDialog(simpledialog.Dialog):
    def body(self, master):
        ttk.Label(master, text="Server IP:").grid(row=0, sticky=tk.W)
        ttk.Label(master, text="Server Port:").grid(row=1, sticky=tk.W)
        ttk.Label(master, text="usbip.exe Path:").grid(row=2, sticky=tk.W)
        ttk.Label(master, text="Username:").grid(row=3, sticky=tk.W)

        self.server_ip_entry = ttk.Entry(master, width=30)
        self.server_ip_entry.grid(row=0, column=1, padx=5, pady=2)
        self.server_ip_entry.insert(0, SERVER_IP)

        self.server_port_entry = ttk.Entry(master, width=10)
        self.server_port_entry.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
        self.server_port_entry.insert(0, str(SERVER_PORT))

        self.usbip_cmd_entry = ttk.Entry(master, width=40)
        self.usbip_cmd_entry.grid(row=2, column=1, padx=5, pady=2)
        self.usbip_cmd_entry.insert(0, USBIP_CMD)

        self.username_entry = ttk.Entry(master, width=30)
        self.username_entry.grid(row=3, column=1, padx=5, pady=2)
        self.username_entry.insert(0, username)
        
        return self.server_ip_entry # initial focus

    def apply(self):
        global SERVER_IP, SERVER_PORT, USBIP_CMD, username, SERVER_URL
        
        new_server_ip = self.server_ip_entry.get().strip()
        new_server_port_str = self.server_port_entry.get().strip()
        new_usbip_cmd = self.usbip_cmd_entry.get().strip()
        new_username = self.username_entry.get().strip()

        if not new_server_ip:
            messagebox.showerror("Validation Error", "Server IP cannot be empty.")
            return # ダイアログを閉じない
        if not new_server_port_str.isdigit() or not (0 < int(new_server_port_str) < 65536):
            messagebox.showerror("Validation Error", "Server Port must be a valid number (1-65535).")
            return
        if not new_usbip_cmd:
             messagebox.showerror("Validation Error", "usbip.exe Path cannot be empty.")
             return
        if not new_username:
             messagebox.showerror("Validation Error", "Username cannot be empty.")
             return

        SERVER_IP = new_server_ip
        SERVER_PORT = int(new_server_port_str)
        USBIP_CMD = new_usbip_cmd
        username = new_username
        
        SERVER_URL = f"http://{SERVER_IP}:{SERVER_PORT}" # SERVER_URLも更新
        
        current_config = {
            "server_ip": SERVER_IP,
            "server_port": SERVER_PORT,
            "usbip_cmd": USBIP_CMD,
            "username": username
        }
        save_config(current_config) # 新しい設定を保存
        update_gui_titles_and_labels() # GUIの表示を更新
        
        # ユーザー名が変更されたらサーバーに通知することも検討
        if my_local_ip != "Unknown":
            threading.Thread(target=register_user_with_server, daemon=True).start()
        
        fetch_and_display_devices_thread() # 設定変更後、リストを再読み込み

def open_settings_dialog():
    # current_config = {"server_ip": SERVER_IP, "server_port": SERVER_PORT, ...} # 必要なら渡す
    dialog = SettingsDialog(root, "Application Settings")
    # applyで保存されるので、ここでは特に結果を受け取らなくても良い
    # if dialog.result:
    #     pass

# --- 関数 (get_my_ip_address_reliably, set_username, register_with_server, unregister_from_server は変更なしのため省略) ---
def get_my_ip_address_reliably():
    global my_local_ip
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5) # 短いタイムアウト
        s.connect((SERVER_IP, SERVER_PORT))
        my_local_ip = s.getsockname()[0]
        s.close()
        if my_local_ip and my_local_ip != "0.0.0.0": return my_local_ip
    except Exception: pass # 失敗しても次の方法へ

    try:
        hostname = socket.gethostname()
        my_local_ip = socket.gethostbyname(hostname)
        if my_local_ip and my_local_ip != "127.0.0.1": return my_local_ip
    except Exception: my_local_ip = "Unknown"
    
    if my_local_ip == "Unknown" or my_local_ip == "127.0.0.1":
        try:
            s_ext = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s_ext.settimeout(0.1)
            s_ext.connect(("8.8.8.8", 80))
            my_local_ip = s_ext.getsockname()[0]
            s_ext.close()
            if my_local_ip and my_local_ip != "0.0.0.0": return my_local_ip
        except Exception: my_local_ip = "Unknown"
    return my_local_ip

def set_username():
    global username
    new_name = simpledialog.askstring("Username", "Enter your username:", initialvalue=username)
    if new_name:
        username = new_name
        root.title(f"USB/IP Client GUI - User: {username} (IP: {my_local_ip})")
        update_status_bar(f"Username set to: {username}")
        # ユーザー名変更時にサーバーに通知する場合 (アタッチ/デタッチ時でも良い)
        if my_local_ip != "Unknown": # IPが分かっていれば
            threading.Thread(target=register_with_server, daemon=True).start()


def register_user_with_server(): # 関数名を変更 (旧register_with_server)
    if my_local_ip == "Unknown":
        print("Warning: Local IP unknown, cannot register user with server yet.")
        return False
    try:
        payload = {"ip_address": my_local_ip, "username": username}
        # APIエンドポイント名を変更
        response = requests.post(f"{SERVER_URL}/register_client_user", json=payload, timeout=5)
        response.raise_for_status()
        update_status_bar(f"User info sent to server: {username} (IP: {my_local_ip})")
        return True
    except requests.exceptions.RequestException as e:
        update_status_bar(f"Error sending user info to server: {e}")
        return False

def unregister_from_server(notify_server=True): # サーバー通知を制御する引数追加
    if not notify_server: # アプリ終了時など、サーバーに通知しない場合
        update_status_bar(f"Local session ended for {username} (IP: {my_local_ip})")
        return True

    if my_local_ip == "Unknown": return False
    try:
        payload = {"ip_address": my_local_ip}
        response = requests.post(f"{SERVER_URL}/unregister_client", json=payload, timeout=5)
        response.raise_for_status()
        update_status_bar(f"Unregistered from server (IP: {my_local_ip})")
        return True
    except requests.exceptions.RequestException as e:
        update_status_bar(f"Error unregistering from server: {e}")
        return False

def fetch_and_display_devices_thread():
    def task():
        print(f"--- fetch_and_display_devices_thread (My IP: {my_local_ip}, User: {username}) ---")
        try:
            response = requests.get(f"{SERVER_URL}/device_status", timeout=10)
            response.raise_for_status()
            server_data = response.json()
            print(f"Server /device_status response: {json.dumps(server_data, indent=2)}")

            devices_tree.delete(*devices_tree.get_children())
            
            # メインは exported_devices_list を使う。statusはサーバーが判断済み。
            exported_devices = server_data.get("exported_devices_list", [])
            
            # current_attachments_managed_by_app も参考にできる (デバッグや補助情報として)
            # app_managed_attachments = server_data.get("current_attachments_managed_by_app", [])

            for dev in exported_devices:
                bus_id = dev.get("bus_id", "N/A")
                description = dev.get("description", "N/A")
                vid = dev.get("vid", "")
                pid = dev.get("pid", "")
                display_desc = f"{description} (VID:{vid} PID:{pid})"
                status_text = dev.get("status", "Unknown") # サーバーが判断したステータス

                is_used_by_me = False
                # ステータス文字列から自分が使っているか判定 (より堅牢なのはサーバーからの専用フラグ)
                if status_text.startswith("In use by:"):
                    # user_info_if_attached フィールドがあるか確認
                    user_info = dev.get("user_info_if_attached") # サーバーが付加した使用者の情報文字列
                    if user_info:
                        if username in user_info and my_local_ip in user_info:
                             is_used_by_me = True
                             status_text = f"Attached by: You ({username})" # 表示を明確に
                    # もし user_info_if_attached がなければ、status_text そのもので判定試行
                    elif username in status_text and my_local_ip in status_text : # 簡易判定
                        is_used_by_me = True
                        status_text = f"Attached by: You ({username})"

                tag = "used_by_me" if is_used_by_me else "other"
                devices_tree.insert("", "end", values=(bus_id, display_desc, status_text), tags=(tag,))
            
            devices_tree.tag_configure("used_by_me", background="lightgreen")

            if not exported_devices:
                update_status_bar("No devices found on server or server data issue.")
            else:
                update_status_bar("Device list refreshed.")
        # ... (エラーハンドリングは同じ) ...
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Server Error", f"Failed to fetch device list from server: {e}")
            update_status_bar(f"Error fetching server list: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            update_status_bar(f"Unexpected error: {e}")
            import traceback; traceback.print_exc()
            
    threading.Thread(target=task, daemon=True).start()


def register_user_with_server(): # 関数名を変更 (旧register_with_server)
    if my_local_ip == "Unknown":
        print("Warning: Local IP unknown, cannot register user with server yet.")
        return False
    try:
        payload = {"ip_address": my_local_ip, "username": username}
        # APIエンドポイント名を変更
        response = requests.post(f"{SERVER_URL}/register_client_user", json=payload, timeout=5)
        response.raise_for_status()
        update_status_bar(f"User info sent to server: {username} (IP: {my_local_ip})")
        return True
    except requests.exceptions.RequestException as e:
        update_status_bar(f"Error sending user info to server: {e}")
        return False

def set_username(): # 変更なしだが、中で register_user_with_server を呼ぶように
    global username
    new_name = simpledialog.askstring("Username", "Enter your username:", initialvalue=username)
    if new_name:
        username = new_name
        root.title(f"USB/IP Client GUI - User: {username} (IP: {my_local_ip})")
        update_status_bar(f"Username set to: {username}")
        if my_local_ip != "Unknown":
            threading.Thread(target=register_user_with_server, daemon=True).start()


def fetch_and_display_devices_thread():
    def task():
        print(f"--- fetch_and_display_devices_thread (My IP: {my_local_ip}, User: {username}) ---")
        try:
            response = requests.get(f"{SERVER_URL}/device_status", timeout=10)
            response.raise_for_status()
            server_data = response.json()
            print(f"Server /device_status response: {json.dumps(server_data, indent=2)}")

            devices_tree.delete(*devices_tree.get_children())
            
            # メインは exported_devices_list を使う。statusはサーバーが判断済み。
            exported_devices = server_data.get("exported_devices_list", [])
            
            # current_attachments_managed_by_app も参考にできる (デバッグや補助情報として)
            # app_managed_attachments = server_data.get("current_attachments_managed_by_app", [])

            for dev in exported_devices:
                bus_id = dev.get("bus_id", "N/A")
                description = dev.get("description", "N/A")
                vid = dev.get("vid", "")
                pid = dev.get("pid", "")
                display_desc = f"{description} (VID:{vid} PID:{pid})"
                status_text = dev.get("status", "Unknown") # サーバーが判断したステータス

                is_used_by_me = False
                # ステータス文字列から自分が使っているか判定 (より堅牢なのはサーバーからの専用フラグ)
                if status_text.startswith("In use by:"):
                    # user_info_if_attached フィールドがあるか確認
                    user_info = dev.get("user_info_if_attached") # サーバーが付加した使用者の情報文字列
                    if user_info:
                        if username in user_info and my_local_ip in user_info:
                             is_used_by_me = True
                             status_text = f"Attached by: You ({username})" # 表示を明確に
                    # もし user_info_if_attached がなければ、status_text そのもので判定試行
                    elif username in status_text and my_local_ip in status_text : # 簡易判定
                        is_used_by_me = True
                        status_text = f"Attached by: You ({username})"

                tag = "used_by_me" if is_used_by_me else "other"
                devices_tree.insert("", "end", values=(bus_id, display_desc, status_text), tags=(tag,))
            
            devices_tree.tag_configure("used_by_me", background="lightgreen")

            if not exported_devices:
                update_status_bar("No devices found on server or server data issue.")
            else:
                update_status_bar("Device list refreshed.")
        # ... (エラーハンドリングは同じ) ...
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Server Error", f"Failed to fetch device list from server: {e}")
            update_status_bar(f"Error fetching server list: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            update_status_bar(f"Unexpected error: {e}")
            import traceback; traceback.print_exc()
            
    threading.Thread(target=task, daemon=True).start()


def attach_device():
    # ... (選択処理、使用中確認はほぼ同じ) ...
    selected_item_iid = devices_tree.focus()
    if not selected_item_iid: messagebox.showwarning("No selection", "Please select a device to attach."); return
    item_values = devices_tree.item(selected_item_iid, "values")
    bus_id = item_values[0]
    item_tags = devices_tree.item(selected_item_iid, "tags")
    is_already_used_by_me = "used_by_me" in item_tags
    if is_already_used_by_me: messagebox.showinfo("Info", f"Device {bus_id} is already attached by you."); return
    current_status_text = item_values[2]
    if current_status_text.startswith("In use by:") or current_status_text.startswith("Attached by:"):
        if not messagebox.askyesno("Confirm Attach", f"Device {bus_id} seems to be in use: '{current_status_text}'.\nAttempt to attach anyway?"): return
    
    # ユーザー情報を先にサーバーに送っておく（最新のユーザー名を使うため）
    if not register_user_with_server():
        update_status_bar(f"Attach aborted: Could not update user info with server.")
        return

    def task_attach(target_bus_id, client_user, client_ip_addr):
        update_status_bar(f"Attempting to attach {target_bus_id}...")
        print(f"[AttachTask] Started for bus_id: {target_bus_id}") # ★デバッグ

        try:
            cmd = [USBIP_CMD, "attach", "-r", SERVER_IP, "-b", target_bus_id]
            print(f"[AttachTask] Executing command: {' '.join(cmd)}") # ★デバッグ
            result = subprocess.run(cmd, capture_output=False, text=True, check=False)
            print(f"[AttachTask] 'usbip attach' successful. STDOUT:\n{result.stdout}") # ★デバッグ
            print(f"[AttachTask] Return Code: {result.returncode}") # ★戻りコード確認
            print(f"[AttachTask] STDOUT:\n{result.stdout}")       # ★標準出力確認
            print(f"[AttachTask] STDERR:\n{result.stderr}")       # ★標準エラー出力確認
            
            # アタッチ成功後、サーバーに通知
            update_status_bar(f"Device {target_bus_id} attached locally. Notifying server...") # ★デバッグ
            print(f"[AttachTask] Notifying server of attach for bus_id: {target_bus_id}") # ★デバッグ
            try:
                notify_payload = {
                    "client_ip": client_ip_addr,
                    "username": client_user,
                    "attached_bus_id": target_bus_id
                }
                print(f"[AttachTask] Notify payload: {notify_payload}") # ★デバッグ
                # タイムアウトを短めに設定してテスト (例: 5秒)
                response_notify = requests.post(f"{SERVER_URL}/notify_attach", json=notify_payload, timeout=10) # タイムアウトを少し延ばすことも検討
                print(f"[AttachTask] Server notify response status: {response_notify.status_code}") # ★デバッグ
                print(f"[AttachTask] Server notify response body: {response_notify.text}") # ★デバッグ
                response_notify.raise_for_status() # HTTPエラーがあればここで例外発生
                print(f"[AttachTask] Successfully notified server of attach: {target_bus_id}") # ★デバッグ
            except requests.exceptions.Timeout:
                print(f"[AttachTask] Error: Timeout notifying server of attach for {target_bus_id}") # ★デバッグ
                messagebox.showwarning("Attach Warning", f"Device {target_bus_id} attached, but server notification timed out.")
            except requests.exceptions.RequestException as notify_e: # より広範なリクエスト例外をキャッチ
                print(f"[AttachTask] Error notifying server of attach: {notify_e}") # ★デバッグ
                messagebox.showwarning("Attach Warning", f"Device {target_bus_id} attached, but failed to notify server: {notify_e}")
            except Exception as notify_generic_e: # その他の予期せぬ例外
                print(f"[AttachTask] Unexpected error during server notification: {notify_generic_e}")
                messagebox.showwarning("Attach Warning", f"Device {target_bus_id} attached, but an unexpected error occurred during server notification: {notify_generic_e}")


            print(f"[AttachTask] Showing success messagebox for {target_bus_id}") # ★デバッグ
            messagebox.showinfo("Success", f"Device {target_bus_id} attached successfully.\nServer has been notified (check server logs for confirmation).")
            update_status_bar(f"Device {target_bus_id} attached and server notified.")
            
            print(f"[AttachTask] Refreshing device list after attach of {target_bus_id}") # ★デバッグ
            fetch_and_display_devices_thread()
            print(f"[AttachTask] Finished for bus_id: {target_bus_id}") # ★デバッグ

        except subprocess.CalledProcessError as e:
            print(f"[AttachTask] 'usbip attach' command failed. STDERR:\n{e.stderr}\nSTDOUT:\n{e.stdout}") # ★デバッグ
            messagebox.showerror("Attach Error", f"Failed to attach device {target_bus_id}:\n{e.stderr or e.stdout or e}")
            update_status_bar(f"Error attaching {target_bus_id}: {e}")
        except Exception as e:
            print(f"[AttachTask] Exception during subprocess.run or subsequent processing: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Attach Error", f"An unexpected error occurred while trying to attach: {e}")
            update_status_bar(f"Unexpected attach error: {e}")
            
    threading.Thread(target=task_attach, args=(bus_id, username, my_local_ip), daemon=True).start() # 引数を渡す

def get_currently_attached_devices_from_treeview():
    """
    統合されたデバイスリスト (devices_tree) から、
    現在自分 (my_local_ip, username) がアタッチしているデバイスの情報を取得する。
    戻り値: リスト of dicts [{"bus_id": "...", "local_port_guess": "..." (あれば)}]
    """
    attached_by_me = []
    if not devices_tree: # GUI要素がまだなければ空
        return []
        
    for item_iid in devices_tree.get_children():
        item_tags = devices_tree.item(item_iid, "tags")
        if "used_by_me" in item_tags:
            values = devices_tree.item(item_iid, "values")
            bus_id = values[0]
            # ローカルポート番号を特定するのは依然として難しいが、
            # デタッチ処理では必要になる。
            # ここでは、もしステータス表示にポート番号が含まれていればそれを採用する試み（現状の表示では難しい）
            # もしくは、アタッチ時にローカルで (bus_id, port) のマッピングを保持するのがベスト。
            # 今回は、デタッチ処理の中で再度 `usbip port` を呼ぶことを想定し、ここではバスIDのみ返す。
            attached_by_me.append({"bus_id": bus_id}) # ポート特定はデタッチ関数に任せる
    return attached_by_me


def detach_single_device(server_bus_id_to_detach, local_port_to_use=None, show_messages=True):
    """
    指定されたサーバーバスIDのデバイスをデタッチするヘルパー関数。
    local_port_to_use が指定されればそれを使う。なければ推測を試みる。
    show_messages: 成功/失敗のメッセージボックスを表示するかどうか。
    戻り値: True (成功/通知成功), False (失敗)
    """
    print(f"[detach_single_device] Detaching {server_bus_id_to_detach}, local_port hint: {local_port_to_use}")

    actual_port_to_detach = local_port_to_use
    if not actual_port_to_detach:
        # ローカルポート番号の特定ロジック (現状の簡易版)
        try:
            cmd_port = [USBIP_CMD, "port"]
            result_port = subprocess.run(cmd_port, capture_output=True, text=True, check=False)
            lines = result_port.stdout.strip().split('\n')
            # このパースは、アタッチ中のデバイスが1つの場合に限定的。
            # 理想は、アタッチ時に記録したポート番号を使うこと。
            # ここでは、最も単純に、最初に見つかった使用中ポートを使う（非常に危険）
            # または、サーバーバスIDと何らかの方法で紐付ける（現状困難）
            
            # 今回は、ポート番号を特定する信頼性の高い方法がないため、
            # ポート00から順番に試すか、あるいはユーザーに入力を促す必要がある。
            # ここでは、デモとして「最初のポート」で試みるが、実用には耐えない。
            # **より堅牢な実装では、アタッチ時にポート番号を記録しておくべき**
            found_any_port = False
            for line in lines:
                port_match = re.match(r"Port\s*(\d+):\s*<Device in Use>", line.strip())
                if port_match:
                    actual_port_to_detach = port_match.group(1)
                    found_any_port = True
                    print(f"  [detach_single_device] Guessed local port {actual_port_to_detach} for {server_bus_id_to_detach}")
                    break # 最初に見つかったもので試す
            if not found_any_port:
                if show_messages: messagebox.showerror("Detach Error", f"Could not determine a local port for device {server_bus_id_to_detach} to detach.")
                print(f"  [detach_single_device] No local port found for {server_bus_id_to_detach}")
                return False
        except Exception as e:
            if show_messages: messagebox.showerror("Detach Error", f"Error determining local port for {server_bus_id_to_detach}: {e}")
            print(f"  [detach_single_device] Exception determining local port for {server_bus_id_to_detach}: {e}")
            return False
    
    if not actual_port_to_detach: # ポートが特定できなかった場合
        print(f"  [detach_single_device] Critical: No local port determined for {server_bus_id_to_detach}")
        return False

    update_status_bar(f"Detaching server BusID {server_bus_id_to_detach} (via local port {actual_port_to_detach})...")
    
    success = False
    try:
        cmd = [USBIP_CMD, "detach", "-p", actual_port_to_detach]
        print(f"  [detach_single_device] Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True) # 成功時は0を返す前提
        
        # デタッチ成功後、サーバーに通知
        try:
            notify_payload = {
                "client_ip": my_local_ip,
                "username": username,
                "detached_bus_id": server_bus_id_to_detach
            }
            response_notify = requests.post(f"{SERVER_URL}/notify_detach", json=notify_payload, timeout=5)
            response_notify.raise_for_status()
            print(f"  [detach_single_device] Successfully notified server of detach: {server_bus_id_to_detach}")
        except Exception as notify_e:
            print(f"  [detach_single_device] Error notifying server of detach: {notify_e}")
            if show_messages: messagebox.showwarning("Detach Warning", f"Device (BusID: {server_bus_id_to_detach}) detached from port {actual_port_to_detach}, but failed to notify server: {notify_e}")
        
        if show_messages: messagebox.showinfo("Success", f"Device (Server BusID: {server_bus_id_to_detach}) detached from port {actual_port_to_detach} successfully.")
        update_status_bar(f"Device {server_bus_id_to_detach} detached from port {actual_port_to_detach}.")
        success = True
    except subprocess.CalledProcessError as e:
        if show_messages: messagebox.showerror("Detach Error", f"Failed to detach device (BusID: {server_bus_id_to_detach}) on port {actual_port_to_detach}:\n{e.stderr or e.stdout or e}")
        update_status_bar(f"Error detaching {server_bus_id_to_detach} on port {actual_port_to_detach}: {e}")
    except Exception as e:
        if show_messages: messagebox.showerror("Error", f"An unexpected error occurred during detach of {server_bus_id_to_detach}: {e}")
        update_status_bar(f"Unexpected detach error for {server_bus_id_to_detach}: {e}")
    
    return success

def detach_device():
    selected_item_iid = devices_tree.focus()
    if not selected_item_iid:
        messagebox.showwarning("No selection", "Please select a device to detach.")
        return

    item_values = devices_tree.item(selected_item_iid, "values")
    item_tags = devices_tree.item(selected_item_iid, "tags")
    
    bus_id_to_detach = item_values[0]
    is_used_by_me = "used_by_me" in item_tags

    if not is_used_by_me:
        messagebox.showerror("Detach Error", f"Device {bus_id_to_detach} is not currently attached by you.\nCannot detach.")
        return

    # detach_single_device は非同期で実行しない（on_closingで順番に処理するため）
    # ただし、UIがブロックされる可能性はあるので、長い場合はスレッド化を検討
    # ここでは、ユーザー操作なのでUIブロックは許容範囲とする
    if detach_single_device(bus_id_to_detach, show_messages=True): # ポートは中で推測
        fetch_and_display_devices_thread() # リストを更新


    update_status_bar(f"Attempting to detach server BusID {bus_id_to_detach} (via local port {local_port_to_detach})...")

    def task_detach(port_num_cmd, server_bus_id, client_ip_addr, client_user): # 引数追加
        try:
            cmd = [USBIP_CMD, "detach", "-p", port_num_cmd]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # デタッチ成功後、サーバーに通知
            try:
                notify_payload = {
                    "client_ip": client_ip_addr, # オプショナルだが、誰の操作かログに残すために
                    "username": client_user,   # 同上
                    "detached_bus_id": server_bus_id
                }
                response_notify = requests.post(f"{SERVER_URL}/notify_detach", json=notify_payload, timeout=5)
                response_notify.raise_for_status()
                print(f"Successfully notified server of detach: {server_bus_id}")
            except Exception as notify_e:
                print(f"Error notifying server of detach: {notify_e}")
                messagebox.showwarning("Detach Warning", f"Device on port {port_num_cmd} detached, but failed to notify server: {notify_e}")

            messagebox.showinfo("Success", f"Device on port {port_num_cmd} (Server BusID: {server_bus_id}) detached successfully.\n{result.stdout}")
            update_status_bar(f"Device on port {port_num_cmd} detached.")
            fetch_and_display_devices_thread()
        # ... (エラーハンドリング) ...
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Detach Error", f"Failed to detach device on port {port_num_cmd}:\n{e.stderr or e.stdout or e}")
            update_status_bar(f"Error detaching port {port_num_cmd}: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred during detach: {e}")
            update_status_bar(f"Unexpected detach error: {e}")

    threading.Thread(target=task_detach, args=(local_port_to_detach, bus_id_to_detach, my_local_ip, username), daemon=True).start() # 引数追加

def manage_server_binding_action(action_type):
    selected_item_iid = devices_tree.focus()
    if not selected_item_iid:
        messagebox.showwarning("No selection", "Please select a device from the list.")
        return

    item_values = devices_tree.item(selected_item_iid, "values")
    bus_id = item_values[0]
    current_status = item_values[2] # "Status / User" カラム

    if action_type == "unbind" and "Available" in current_status: # ステータスが "Available" なら既にアンバインドされている可能性
         if not messagebox.askyesno("Confirm Unbind", f"Device {bus_id} seems to be already available (possibly unbound).\nStill attempt to unbind on server?"):
             return
    elif action_type == "bind" and "Available" not in current_status: # ステータスが "Available" でないなら既にバインドされている可能性
         if not messagebox.askyesno("Confirm Bind", f"Device {bus_id} does not seem to be 'Available' (possibly already bound or in use).\nStill attempt to bind on server?"):
             return

    confirm_message = f"Are you sure you want to '{action_type}' device {bus_id} on the server?"
    if action_type == "unbind" and "In use by" in current_status:
        confirm_message += f"\n\nWARNING: This device is reported as '{current_status}'.\nUnbinding it will forcibly disconnect the user!"
    
    if not messagebox.askyesno(f"Confirm Server {action_type.capitalize()}", confirm_message):
        return

    payload = {"action": action_type, "bus_id": bus_id}
    update_status_bar(f"Requesting server to '{action_type}' device {bus_id}...")

    def task():
        try:
            response = requests.post(f"{SERVER_URL}/manage_server_device_binding", json=payload, timeout=15) # 少し長めのタイムアウト
            
            # レスポンスボディをJSONとしてパース試行
            try:
                response_data = response.json()
                message_from_server = response_data.get("message", response_data.get("error", "No message from server."))
                stdout_from_server = response_data.get("stdout", "")
                stderr_from_server = response_data.get("stderr", "")
                details = f"\nServer stdout:\n{stdout_from_server}\nServer stderr:\n{stderr_from_server}"
            except ValueError: # JSONデコードエラー
                message_from_server = response.text # 生のテキストをメッセージとして使う
                details = ""

            if response.ok: # 2xx系ステータスコード
                messagebox.showinfo(f"Server {action_type.capitalize()} Status", f"{message_from_server}{details}")
                update_status_bar(f"Server '{action_type}' for {bus_id} reported: {response.status_code}")
            else: # 4xx, 5xx系
                messagebox.showerror(f"Server {action_type.capitalize()} Error ({response.status_code})", f"{message_from_server}{details}")
                update_status_bar(f"Error from server on '{action_type}' for {bus_id}: {response.status_code}")

            fetch_and_display_devices_thread() # リストを更新して状態の変化を反映
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", f"Failed to send '{action_type}' request to server: {e}")
            update_status_bar(f"Network error on '{action_type}' for {bus_id}: {e}")
        except Exception as e:
            messagebox.showerror("Client Error", f"An unexpected error occurred: {e}")
            update_status_bar(f"Client error on '{action_type}' for {bus_id}: {e}")
            import traceback; traceback.print_exc()

    threading.Thread(target=task, daemon=True).start()


def force_detach_all_on_server():
    if not messagebox.askyesno("Confirm Force Detach All", 
                               "WARNING: This will attempt to forcibly detach ALL currently attached USB devices on the server.\n"
                               "This may interrupt users and cause data loss.\n\nAre you absolutely sure?"):
        return

    update_status_bar("Requesting server to force detach all devices...")

    def task():
        try:
            response = requests.post(f"{SERVER_URL}/force_detach_all_server_devices", json={}, timeout=30) # タイムアウト長め

            try:
                response_data = response.json()
                message_from_server = response_data.get("message", "No message from server.")
                errors_from_server = response_data.get("errors")
            except ValueError:
                message_from_server = response.text
                errors_from_server = None

            if response.ok or response.status_code == 207: # 200 OK or 207 Multi-Status
                info_title = "Force Detach All Status"
                if response.status_code == 207:
                    info_title = "Force Detach All (Partial Success)"
                
                full_message = message_from_server
                if errors_from_server:
                    full_message += "\n\nErrors for specific devices:\n"
                    for err_item in errors_from_server:
                        for bus_id_err, msg_err in err_item.items():
                            full_message += f" - {bus_id_err}: {msg_err}\n"
                messagebox.showinfo(info_title, full_message)
                update_status_bar(f"Server force detach all reported: {response.status_code}")
            else:
                messagebox.showerror(f"Force Detach All Error ({response.status_code})", message_from_server)
                update_status_bar(f"Error from server on force detach all: {response.status_code}")

            fetch_and_display_devices_thread() # リストを更新
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", f"Failed to send force detach all request to server: {e}")
            update_status_bar(f"Network error on force detach all: {e}")
        except Exception as e:
            messagebox.showerror("Client Error", f"An unexpected error occurred: {e}")
            update_status_bar(f"Client error on force detach all: {e}")
            import traceback; traceback.print_exc()
            
    threading.Thread(target=task, daemon=True).start()

def update_status_bar(message):
    status_var.set(message)
    print(message)

def on_closing():
    """ウィンドウが閉じられるときの処理"""
    print("Application closing...")
    update_status_bar("Application closing, detaching devices if any...")

    attached_devices = get_currently_attached_devices_from_treeview()
    
    if not attached_devices:
        print("No devices attached by this client. Exiting.")
        root.destroy()
        return

    if messagebox.askyesno("Confirm Exit", 
                           f"There are {len(attached_devices)} device(s) attached.\n"
                           "Do you want to detach them before exiting?"):
        
        all_detached_successfully = True
        for dev_info in attached_devices:
            bus_id = dev_info["bus_id"]
            print(f"Attempting to detach {bus_id} before exiting...")
            # on_closing時はメッセージボックスを抑制し、ステータスバーで通知
            if not detach_single_device(bus_id, show_messages=False):
                all_detached_successfully = False
                update_status_bar(f"Failed to detach {bus_id} on exit. Please check manually.")
                # ここで処理を中断するか、ユーザーに選択させることもできる
                if not messagebox.askretrycancel("Detach Failed", f"Failed to detach {bus_id}.\nRetry or cancel exit? (Cancel will exit without detaching this device)"):
                    # キャンセルを選んだら、このデバイスはデタッチせずに終了処理へ
                    # (あるいは、アプリ終了を完全にキャンセルする選択肢も)
                    print(f"User chose to cancel exit or skip detaching {bus_id}.")
                    # break # ループを抜けて終了処理へ (このデバイスはデタッチされない)
                    # continue # 次のデバイスのデタッチへ (このデバイスはデタッチされない)
                    # ここでは、とりあえず続行するが、失敗したことは記録
                    pass # all_detached_successfully = False のまま
            else:
                update_status_bar(f"Device {bus_id} detached on exit.")
        
        if all_detached_successfully:
            update_status_bar("All devices detached. Exiting.")
        else:
            update_status_bar("Some devices may not have been detached. Exiting.")
        
        # デタッチ処理後、短時間待ってからリストを更新し、終了
        # root.after(1000, lambda: (fetch_and_display_devices_thread(), root.after(500, root.destroy)))
        # fetch_and_display_devices_thread() # UI更新は終了直前なので不要かもしれない
    else:
        update_status_bar("Exiting without detaching devices.")

    print("Exiting application now.")
    root.destroy()

# --- GUI作成 ---
root = tk.Tk()
load_config() # ★★★ アプリ起動時に設定を読み込む ★★★
my_local_ip = get_my_ip_address_reliably()
update_gui_titles_and_labels() # ★★★ 初期タイトルなどを設定値で更新 ★★★
root.protocol("WM_DELETE_WINDOW", on_closing) # 閉じるボタンの処理

menubar = tk.Menu(root)
filemenu = tk.Menu(menubar, tearoff=0)
# filemenu.add_command(label="Set Username", command=set_username)
filemenu.add_command(label="Settings", command=open_settings_dialog) # ★Settingsメニュー追加
filemenu.add_command(label="Refresh My IP", command=lambda: root.title(f"USB/IP Client GUI - User: {username} (IP: {get_my_ip_address_reliably()})"))
filemenu.add_separator()
filemenu.add_command(label="Exit", command=on_closing)
menubar.add_cascade(label="File", menu=filemenu)
root.config(menu=menubar)

main_frame = ttk.Frame(root, padding="10")
main_frame.grid(row=0, column=0, sticky="nsew")
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

# --- 統合されたデバイスリストフレーム ---
devices_frame = ttk.LabelFrame(main_frame, text=f"USB Devices on Server ({SERVER_IP})", padding="10")
devices_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
main_frame.rowconfigure(0, weight=1) # フレームを行いっぱいに拡張
main_frame.columnconfigure(0, weight=1)

devices_tree = ttk.Treeview(devices_frame, columns=("bus_id", "description", "status"), show="headings", height=15)
devices_tree.heading("bus_id", text="Bus ID (Server)")
devices_tree.heading("description", text="Description (VID:PID)")
devices_tree.heading("status", text="Status / User")
devices_tree.column("bus_id", width=120, anchor="w")
devices_tree.column("description", width=330, anchor="w")
devices_tree.column("status", width=250, anchor="w") # ステータス表示幅を少し広げる
devices_tree.pack(side="left", fill="both", expand=True)

devices_scrollbar = ttk.Scrollbar(devices_frame, orient="vertical", command=devices_tree.yview)
devices_scrollbar.pack(side="right", fill="y")
devices_tree.configure(yscrollcommand=devices_scrollbar.set)

refresh_devices_button = ttk.Button(devices_frame, text="Refresh Device List", command=fetch_and_display_devices_thread)
refresh_devices_button.pack(pady=5, side="bottom", fill="x")


# --- Action Buttons Frame (右側) ---
action_frame = ttk.Frame(main_frame, padding="10")
action_frame.grid(row=0, column=1, padx=5, pady=5, sticky="ns")

attach_button = ttk.Button(action_frame, text="Attach Selected", command=attach_device)
attach_button.pack(pady=10, fill="x")
detach_button = ttk.Button(action_frame, text="Detach Selected", command=detach_device)
detach_button.pack(pady=10, fill="x")

ttk.Separator(action_frame, orient='horizontal').pack(fill='x', pady=10) # 区切り線

bind_button = ttk.Button(action_frame, text="Bind on Server", command=lambda: manage_server_binding_action("bind"))
bind_button.pack(pady=5, fill="x")

unbind_button = ttk.Button(action_frame, text="Unbind on Server", command=lambda: manage_server_binding_action("unbind"))
unbind_button.pack(pady=5, fill="x")

ttk.Separator(action_frame, orient='horizontal').pack(fill='x', pady=10)

force_detach_all_button = ttk.Button(action_frame, text="Force Detach All (Server)", command=force_detach_all_on_server, style="Danger.TButton")
force_detach_all_button.pack(pady=10, fill="x")

# スタイルの定義 (もし Danger.TButton を使うなら)
style = ttk.Style()
style.configure("Danger.TButton", foreground="red", font=('Helvetica', '10', 'bold'))

# --- Status Bar ---
status_var = tk.StringVar()
status_bar = ttk.Label(root, textvariable=status_var, relief=tk.SUNKEN, anchor=tk.W, padding="2 5")
status_bar.grid(row=1, column=0, columnspan=2, sticky="ew") # columnspan=2 で両方のカラムにまたがる
update_status_bar("Ready. Set username and server IP if needed.")

if __name__ == '__main__': # PyInstaller対策としてよく使われる
    # (このブロックは、スクリプトが直接実行された場合にのみ実行される)
    # 既にグローバルスコープで load_config() が呼ばれているので、
    # ここでの特別な初期化は少ないかもしれない。

    # 初回起動時に設定ファイルがなければ、ユーザーに設定を促すこともできる
    if not os.path.exists(get_config_file_path()):
        messagebox.showinfo("Initial Setup", "Configuration file not found. Please set your preferences via File > Settings.")
        # open_settings_dialog() # 初回にダイアログを強制的に開く場合

    fetch_and_display_devices_thread() # 初期リスト表示
    root.mainloop()