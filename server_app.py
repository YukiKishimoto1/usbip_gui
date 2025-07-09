# server_app.py

from flask import Flask, request, jsonify
import subprocess
import re
import json
import os
import threading
# import traceback # デバッグ用

app = Flask(__name__)

# --- 設定 ---
CLIENT_USER_INFO_FILE = 'client_user_data.json' # ユーザー名とIPのマッピング用
ATTACHED_DEVICES_LOG_FILE = 'attached_devices_log.json' # 現在アタッチ中のデバイス情報
file_lock_user = threading.Lock()
file_lock_attach = threading.Lock()

# --- グローバル変数 ---
client_user_info = {} # { "ip_address": "username" }
attached_devices_log = {} # { "server_bus_id": {"client_ip": "...", "username": "...", "timestamp": "..."} }

# --- ヘルパー関数 (ユーザー情報管理) ---
def load_client_user_info():
    global client_user_info
    with file_lock_user:
        if os.path.exists(CLIENT_USER_INFO_FILE):
            try:
                with open(CLIENT_USER_INFO_FILE, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict): client_user_info = data
                    else: client_user_info = {}
            except Exception: client_user_info = {}
        else: client_user_info = {}
    print(f"Loaded client user info: {client_user_info}")

def save_client_user_info():
    with file_lock_user:
        try:
            with open(CLIENT_USER_INFO_FILE, 'w') as f:
                json.dump(client_user_info, f, indent=4)
        except Exception as e: print(f"Error saving client user info: {e}")
    print(f"Saved client user info: {client_user_info}")

# --- ヘルパー関数 (アタッチ情報管理) ---
def load_attached_devices_log():
    global attached_devices_log
    with file_lock_attach:
        if os.path.exists(ATTACHED_DEVICES_LOG_FILE):
            try:
                with open(ATTACHED_DEVICES_LOG_FILE, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict): attached_devices_log = data
                    else: attached_devices_log = {}
            except Exception: attached_devices_log = {}
        else: attached_devices_log = {}
    print(f"Loaded attached devices log: {attached_devices_log}")

def save_attached_devices_log():
    with file_lock_attach:
        try:
            with open(ATTACHED_DEVICES_LOG_FILE, 'w') as f:
                json.dump(attached_devices_log, f, indent=4)
        except Exception as e: print(f"Error saving attached devices log: {e}")
    print(f"Saved attached devices log: {attached_devices_log}")


# `usbip list -l` の出力をパースする関数 (前回と同じ、またはご提示の形式に合わせたもの)
def parse_usbip_list_l_output(output_str): # server_app_v3.py の parse_specific_usbip_list_l_output を流用
    devices = []
    lines = output_str.strip().split('\n')
    i = 0
    while i < len(lines):
        line1 = lines[i].strip(); i += 1
        busid_match = re.match(r'-\s*busid\s+([\w\.-]+)\s*\((\w{4}:\w{4})\)', line1)
        if busid_match:
            busid = busid_match.group(1)
            vid_pid_busid_line = busid_match.group(2)
            vid_busid, pid_busid = vid_pid_busid_line.split(':')
            description = f"Device {busid} (VID:{vid_busid} PID:{pid_busid})"
            vid_desc_line, pid_desc_line = vid_busid, pid_busid
            if i < len(lines):
                line2 = lines[i].strip()
                if line2:
                    desc_vid_pid_match = re.search(r'\((\w{4}:\w{4})\)$', line2)
                    if desc_vid_pid_match:
                        vid_pid_from_desc = desc_vid_pid_match.group(1)
                        vid_desc_line, pid_desc_line = vid_pid_from_desc.split(':')
                        description_text_only = re.sub(r'\s*\(\w{4}:\w{4}\)$', '', line2).strip()
                        if description_text_only: description = description_text_only
                    else: description = line2
                    i += 1
            devices.append({"bus_id": busid, "description": description, "vid": vid_desc_line, "pid": pid_desc_line})
        while i < len(lines) and not lines[i].strip(): i += 1
    return devices


# --- API エンドポイント ---
@app.route('/register_client_user', methods=['POST']) # ユーザー情報登録用 (旧register_client)
def register_client_user():
    global client_user_info
    data = request.json
    ip_address = data.get('ip_address')
    username = data.get('username')
    if ip_address and username:
        client_user_info[ip_address] = username
        save_client_user_info()
        print(f"Client user registered/updated: {ip_address} as {username}")
        return jsonify({"message": "Client user info registered/updated"}), 200
    return jsonify({"error": "Missing IP or username"}), 400

# 旧 unregister_client は、ユーザー情報からは削除しない方針に変更も可
# (ユーザー名は保持し、アタッチ情報だけクリアする)
# もしユーザー情報自体を消すならこのままでも良いが、今回はアタッチ情報で制御

@app.route('/notify_attach', methods=['POST'])
def notify_attach():
    global attached_devices_log
    data = request.json
    client_ip = data.get('client_ip')
    username = data.get('username') # クライアントから申告されたユーザー名
    attached_bus_id = data.get('attached_bus_id')
    
    if not (client_ip and username and attached_bus_id):
        return jsonify({"error": "Missing client_ip, username, or attached_bus_id"}), 400

    # 念のため、ユーザー情報を更新/確認
    if client_ip not in client_user_info or client_user_info[client_ip] != username:
        client_user_info[client_ip] = username
        save_client_user_info() # ユーザー情報を更新

    attached_devices_log[attached_bus_id] = {
        "client_ip": client_ip,
        "username": username,
        "timestamp": json.dumps(str(datetime.datetime.now())) # datetimeをインポートする必要あり
    }
    save_attached_devices_log()
    print(f"Device attached: {attached_bus_id} by {username} ({client_ip})")
    return jsonify({"message": f"Attachment of {attached_bus_id} by {username} logged"}), 200


@app.route('/notify_detach', methods=['POST'])
def notify_detach():
    global attached_devices_log
    data = request.json
    # client_ip = data.get('client_ip') # 通知元確認用
    detached_bus_id = data.get('detached_bus_id')

    if not detached_bus_id:
        return jsonify({"error": "Missing detached_bus_id"}), 400

    if detached_bus_id in attached_devices_log:
        detached_info = attached_devices_log.pop(detached_bus_id) # popで削除しつつ情報を取得
        save_attached_devices_log()
        print(f"Device detached: {detached_bus_id} (was used by {detached_info.get('username')})")
        return jsonify({"message": f"Detachment of {detached_bus_id} logged"}), 200
    else:
        print(f"Detachment notification for non-logged bus_id: {detached_bus_id}")
        return jsonify({"message": f"Detachment of {detached_bus_id} (not found in log) noted"}), 200


@app.route('/device_status', methods=['GET'])
def device_status():
    print("[device_status] Request received.")
    exported_devices_list_from_cmd = []
    try:
        # usbip list -l の実行 (sudoers設定が前提)
        cmd_list_local = ['usbip', 'list', '-l'] # ご提示の出力形式に合わせたコマンド
        result_list_cmd = subprocess.run(cmd_list_local, capture_output=True, text=True, check=False)
        if result_list_cmd.returncode == 0:
            parsed_cmd_devices = parse_usbip_list_l_output(result_list_cmd.stdout)
            exported_devices_list_from_cmd = parsed_cmd_devices
        else:
            print(f"Error executing '{' '.join(cmd_list_local)}': {result_list_cmd.stderr or result_list_cmd.stdout}")
    except Exception as e:
        print(f"Exception executing usbip list -l: {e}")

    # 現在アタッチされているデバイスのログをロード (念のため最新化)
    load_attached_devices_log() # 最新のattached_devices_logを読み込む

    final_device_list = []
    for dev_from_cmd in exported_devices_list_from_cmd:
        bus_id = dev_from_cmd["bus_id"]
        status_text = "Available"
        user_info_str = "" # 誰が使っているかの文字列

        if bus_id in attached_devices_log:
            attach_info = attached_devices_log[bus_id]
            user_info_str = f"{attach_info.get('username', 'Unknown')} ({attach_info.get('client_ip', 'N/A')})"
            status_text = f"In use by: {user_info_str}"
        
        final_device_list.append({
            "bus_id": bus_id,
            "description": dev_from_cmd["description"],
            "vid": dev_from_cmd["vid"],
            "pid": dev_from_cmd["pid"],
            "status": status_text, # サーバーが判断したステータス
            "user_info_if_attached": user_info_str if bus_id in attached_devices_log else None
        })
    
    # attached_devices_detailed は、このアプリケーションが管理するアタッチ情報そのもの
    # サーバーのusbip portに依存しない
    current_attachments_for_client_api = []
    for bus_id, info in attached_devices_log.items():
        current_attachments_for_client_api.append({
            "bus_id": bus_id,
            "client_ip": info.get("client_ip"),
            "username": info.get("username"),
            "timestamp": info.get("timestamp")
            # description は exported_devices_list_from_cmd から引く必要がある
        })


    response_data = {
        "exported_devices_list": final_device_list, # これがメインのリスト
        # "attached_devices_log_for_debug": attached_devices_log # デバッグ用に生のログを返すこともできる
        "current_attachments_managed_by_app": current_attachments_for_client_api, # アプリ管理のアタッチ情報
        "app_managed_attachments": attached_devices_log   # アプリが管理するアタッチ情報
    }
    print(f"[device_status] Sending response: {json.dumps(response_data, indent=2)}")
    return jsonify(response_data)

@app.route('/manage_server_device_binding', methods=['POST'])
def manage_server_device_binding():
    global attached_devices_log # アンバインド時にアタッチ情報をクリアするため
    data = request.json
    action = data.get('action') # "bind" or "unbind"
    bus_id = data.get('bus_id')

    if not action or not bus_id or action not in ["bind", "unbind"]:
        return jsonify({"error": "Missing or invalid action or bus_id"}), 400

    cmd = []
    if action == "bind":
        cmd = ['usbip', 'bind', '-b', bus_id]
    elif action == "unbind":
        cmd = ['usbip', 'unbind', '-b', bus_id]

    try:
        print(f"Executing server command: {' '.join(cmd)}")
        # sudoers設定が前提
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            message = f"Device {bus_id} {action} successful."
            if action == "unbind":
                # アンバインド成功時、もしこのデバイスがアタッチログにあれば削除
                if bus_id in attached_devices_log:
                    detached_info = attached_devices_log.pop(bus_id)
                    save_attached_devices_log()
                    message += f" Cleared attachment log for {bus_id} (was used by {detached_info.get('username')})."
                    print(f"Unbind cleared attachment log for {bus_id}")
            print(message)
            return jsonify({"message": message, "stdout": result.stdout, "stderr": result.stderr}), 200
        else:
            error_message = f"Failed to {action} device {bus_id}."
            print(f"{error_message} RC: {result.returncode}, Error: {result.stderr or result.stdout}")
            return jsonify({"error": error_message, "stdout": result.stdout, "stderr": result.stderr}), 500
    except Exception as e:
        error_message = f"Exception during server device {action} for {bus_id}: {e}"
        print(error_message)
        import traceback; traceback.print_exc()
        return jsonify({"error": error_message}), 500


@app.route('/force_detach_all_server_devices', methods=['POST'])
def force_detach_all_server_devices():
    global attached_devices_log
    print("Received request to force detach all server devices.")
    
    detached_count = 0
    errors = []
    
    # attached_devices_log のキーのリストのコピーに対してイテレートする（ループ中に辞書を変更するため）
    bus_ids_to_detach = list(attached_devices_log.keys())

    if not bus_ids_to_detach:
        return jsonify({"message": "No devices were attached according to the log. Nothing to detach."}), 200

    for bus_id in bus_ids_to_detach:
        cmd = ['usbip', 'unbind', '-b', bus_id] # アンバインドで強制的に切断
        try:
            print(f"  Attempting to unbind (force detach) device: {bus_id}")
            # sudoers設定が前提
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                print(f"    Successfully unbound {bus_id}.")
                if bus_id in attached_devices_log: # 再確認（他リクエストで変更されてる可能性も微小ながらある）
                    detached_info = attached_devices_log.pop(bus_id) # ログから削除
                    print(f"    Cleared attachment log for {bus_id} (was used by {detached_info.get('username')}).")
                detached_count += 1
            else:
                error_msg = f"Failed to unbind {bus_id}: {result.stderr or result.stdout}"
                print(f"    {error_msg}")
                errors.append({bus_id: error_msg})
        except Exception as e:
            error_msg = f"Exception unbinding {bus_id}: {e}"
            print(f"    {error_msg}")
            errors.append({bus_id: error_msg})
            import traceback; traceback.print_exc()

    save_attached_devices_log() # 変更を保存

    if not errors:
        return jsonify({"message": f"Successfully forced detach for {detached_count} device(s)."}), 200
    else:
        return jsonify({
            "message": f"Forced detach attempted. Success: {detached_count}. Errors occurred for some devices.",
            "errors": errors
        }), 207 # Multi-Status

# --- アプリケーション起動時の処理 ---
if __name__ == '__main__':
    import datetime # notify_attach で使うのでここでインポート
    import os       # ファイル削除のためにインポート

    # --- 起動時にアタッチ情報ログをクリアする処理 ---
    attach_log_path = ATTACHED_DEVICES_LOG_FILE # グローバルで定義したファイル名
    if os.path.exists(attach_log_path):
        try:
            print(f"Clearing previous attachment log: {attach_log_path}")
            os.remove(attach_log_path)
            print("Attachment log cleared successfully.")
        except OSError as e:
            print(f"Error clearing attachment log file: {e}")
            # ファイルがロックされているなどの理由で削除に失敗した場合でも、
            # アプリの起動は続行する。ただし、ログにはエラーを残す。
    else:
        print("No previous attachment log found. Starting fresh.")
    
    load_client_user_info()
    load_attached_devices_log()
    if os.geteuid() != 0: # rootチェック
        print("Warning: Server not running as root. 'usbip' commands might require sudo privileges.")
    app.run(host='0.0.0.0', port=5000, debug=True)