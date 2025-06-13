# USB/IP GUI クライアント & サーバー

ネットワーク経由でUSBデバイスを共有するためのPython製GUIクライアントアプリケーションと、Raspberry Pi（または他のLinuxマシン）で動作するサーバーアプリケーションです。

## 機能

**サーバー側 (Raspberry Piなど Linux向け)**

*   ローカルに接続されたUSBデバイスをネットワークに公開 (バインド/アンバインド)。
*   アタッチされたデバイスとクライアント情報を記録・管理。
*   クライアントからのアタッチ/デタッチ通知を受信。
*   クライアントからのバインド/アンバインド指示を受信。
*   クライアントからの全アタッチ強制解除指示を受信。
*   現在のデバイス状況をAPI経由でクライアントに提供。

**クライアント側 (Windows向けGUI)**

*   設定ファイル (`client_config.json`) からサーバー情報、`usbip.exe` のパス、ユーザー名を読み込み・保存。GUIから設定変更可能。
*   指定したUSB/IPサーバーに接続。
*   サーバー上で共有可能なUSBデバイスの一覧と使用状況を表示。
*   選択したUSBデバイスをアタッチ/デタッチ。
*   サーバー上のUSBデバイスのバインド/アンバインドを指示。
*   サーバー上の全アタッチ済みUSBデバイスの強制デタッチを指示。
*   アプリケーション終了時にアタッチ中のデバイスを自動的にデタッチするオプション。
*   ユーザー名を設定し、サーバーに使用者情報として通知。

## 必要なもの

### サーバー側 (例: Raspberry Pi)

*   Linux OS (Raspberry Pi OSなど)
*   Python 3.x
*   `usbip` コマンドラインツール
    *   通常、`sudo apt update && sudo apt install usbip` でインストールできます。
*   Flask (Pythonライブラリ)
    *   `pip3 install Flask`
*   (オプション) `requests` (Pythonライブラリ) - 現在のサーバーコードでは直接は使用していませんが、将来的な拡張で必要になる可能性があります。
*   `sudoers` の設定（後述）

### クライアント側 (Windows)

*   Windows OS
*   Python 3.x (もしソースコードから実行する場合)
*   必要なPythonライブラリ (もしソースコードから実行する場合):
    *   Tkinter (通常Pythonに標準で付属)
    *   `requests`: `pip3 install requests`
*   **USB/IP for Windows (usbip-win)**:
    *   **VHCIドライバ**: ネットワーク経由のUSBデバイスを仮想USBホストコントローラとして認識させるために必須です。
    *   **`usbip.exe` コマンドラインツール**: クライアントアプリが内部で使用します。

## クライアント側の準備 (Windows)

### 1. USB/IP for Windows (usbip-win) のインストール

クライアントPCでUSB/IPプロトコルを利用可能にするために、`usbip-win` をインストールします。

**a. `usbip-win-0.3.6-dev` (または最新版) のダウンロードと展開**

   *   **ダウンロード元**: [https://github.com/cezanne/usbip-win/releases](https://github.com/cezanne/usbip-win/releases)
       (上記は一例です。最新の信頼できるソースからダウンロードしてください。)
   *   `usbip-win-X.Y.Z.zip`のようなファイルをダウンロードし、任意のフォルダに展開します (例: `C:\usbip-win`)。
   *   このフォルダには `usbip.exe` やドライバ関連ファイルが含まれています。

**b. VHCI (Virtual Host Controller Interface) ドライバのインストール**

   1.  展開した `usbip-win` フォルダ内にある `usbip_vhci.inf` (または類似の .inf ファイル) を見つけます。
   2.  コマンドプロンプトを**管理者として実行**します。
   3.  以下のコマンドを実行してドライバをインストールします (パスは適宜変更してください)。
       ```cmd
       pnputil /add-driver C:\path\to\usbip-win\usbip_vhci.inf /install
       ```
       (古いバージョンの `usbip-win` では `usbip_install.exe -i` のようなインストーラーが提供されていたこともあります。ドキュメントに従ってください。)
   4.  デバイスマネージャーを開き、「USB コントローラー」または「システム デバイス」の項目に「USB/IP VHCI」のようなデバイスが表示されれば、ドライバのインストールは成功です。

**c. (オプション) `usbipd-win` のインストール**

   *   **ダウンロード元**: (例: 適切な提供元を探してください。例として `usbipd-win_5.1.0_x64.msi` が挙げられていましたが、提供元と最新性を確認してください。)
   *   **インストール**: ダウンロードした `.msi` ファイルを実行し、指示に従ってインストールします。
   *   **注意**: このクライアントアプリケーションは、主にLinuxサーバーと通信することを想定しています。WindowsマシンをUSB/IPサーバーとして運用する場合や、`usbip-win` の特定の機能で `usbipd.exe` がクライアント側でも必要な場合にこの手順を実施してください。

**d. `usbip.exe` のパス設定**
   クライアントアプリケーションのGUIメニュー「File」→「Settings」から、`usbip.exe` へのフルパスを設定できます。または、`usbip.exe` があるフォルダをシステムの環境変数 `PATH` に追加しておけば、設定で単に `usbip` と指定するだけで動作します。

## サーバー側の準備 (Linux)

1.  **Pythonと必要なライブラリのインストール**:
    ```bash
    sudo apt update
    sudo apt install python3 python3-pip usbip
    pip3 install Flask
    ```
2.  **`sudoers` の設定**:
    サーバーアプリケーションが内部で `usbip port`, `usbip list -l`, `usbip bind`, `usbip unbind` コマンドを管理者権限で実行できるように設定します。
    `sudo visudo` コマンドで `/etc/sudoers` ファイルを開き、以下の行を追記します (`your_server_user` は実際にサーバーアプリを実行するユーザー名に、`/path/to/usbip` は `which usbip` で確認した実際のパスに置き換えてください)。

    ```sudoers
    your_server_user ALL=(ALL) NOPASSWD: /path/to/usbip port
    your_server_user ALL=(ALL) NOPASSWD: /path/to/usbip list -l
    your_server_user ALL=(ALL) NOPASSWD: /path/to/usbip bind -b *
    your_server_user ALL=(ALL) NOPASSWD: /path/to/usbip unbind -b *
    ```
    例: ユーザーが `usbip` で、パスが `/usr/sbin/usbip` の場合:
    ```sudoers
    usbip ALL=(ALL) NOPASSWD: /usr/sbin/usbip port
    usbip ALL=(ALL) NOPASSWD: /usr/sbin/usbip list -l
    usbip ALL=(ALL) NOPASSWD: /usr/sbin/usbip bind -b *
    usbip ALL=(ALL) NOPASSWD: /usr/sbin/usbip unbind -b *
    ```

## 実行方法

### サーバー側

1.  サーバーアプリケーションのソースコード (`server_app.py` など) をサーバーに配置します。
2.  ターミナルでそのディレクトリに移動し、実行します (例: `your_server_user` で実行)。
    ```bash
    python3 server_app.py
    ```
    (systemdサービスとして登録して自動起動させることを推奨します。詳細は `systemd` の設定方法を参照してください。)

### クライアント側

**方法1: Pythonソースコードから実行 (開発・テスト向け)**

1.  クライアントアプリケーションのソースコード (`client_gui.py` など) と、必要なPythonライブラリ (`requests`) をインストールしたPython環境を用意します。
2.  初回起動時、またはメニューの「File」→「Settings」から、以下の設定を行います。設定は `client_config.json` というファイルに保存されます（スクリプトと同じディレクトリ、または.exeと同じディレクトリ）。
    *   **Server IP**: 接続先のUSB/IPサーバーのIPアドレス。
    *   **Server Port**: サーバーのポート番号 (デフォルト: 5000)。
    *   **usbip.exe Path**: `usbip.exe` へのフルパス、または環境変数PATHが通っていれば単に `usbip`。
    *   **Username**: サーバーに通知する任意のユーザー名。
3.  コマンドプロンプトまたはターミナルで実行します。
    ```bash
    python client_gui.py
    ```

**方法2: 配布用の.exeファイルを実行 (PyInstallerで作成した場合)**

1.  提供されている `.exe` ファイル (例: `client_gui.exe`) を実行します。
2.  初回起動時は、`client_config.json` が存在しないため、デフォルト設定で起動します。メニューの「File」→「Settings」から設定を行ってください。設定内容は `.exe` ファイルと同じディレクトリに `client_config.json` として保存されます。
3.  実行時に「発行元不明」の警告が表示されることがありますが、これは実行ファイルにデジタル署名がないためです。信頼できるソースからのファイルであれば、「詳細情報」→「実行」を選択して進めてください。管理者権限が必要な場合は、UACプロンプトが表示されます。

## 設定ファイル (`client_config.json`)

クライアントアプリケーションは、以下の設定を `client_config.json` という名前のJSONファイルに保存・読み込みします。このファイルは、スクリプトまたは.exeファイルと同じディレクトリに作成されます。

```json
{
    "server_ip": "192.168.1.100",
    "server_port": 5000,
    "usbip_cmd": "usbip",
    "username": "MyUser"
}
```

### サーバー側

*   `server_app.py`内で、ログファイルの保存場所などを設定できます（現在は `client_user_data.json`, `attached_devices_log.json` がスクリプトと同じディレクトリに作成されます）。
*   デフォルトのポートは `5000` です。

### クライアント側

*   `client_gui.py` の先頭にある `SERVER_IP` 変数に、接続先のUSB/IPサーバーのIPアドレスを設定してください。
*   `USBIP_CMD` 変数に、`usbip.exe` コマンドへのフルパス、または環境変数PATHが通っていれば単に `usbip` を設定してください。

## 既知の問題点と今後の課題

*   **クライアントのデタッチ処理におけるローカルポート番号特定**:
    現在、クライアントがデバイスをデタッチする際に、対応するローカルポート番号を特定するロジックが簡易的です。複数のデバイスをアタッチしている場合、意図しないデバイスをデタッチしてしまう可能性があります。アタッチ時にローカルポート番号とサーバーバスIDのマッピングをクライアント側で記録・管理する堅牢な仕組みが必要です。
*   **サーバーIPアドレスの動的設定**:
    現状、クライアントアプリはソースコードにサーバーIPをハードコーディングしています。GUIから設定変更・保存できるようにするか、起動時に設定ファイルを読み込むなどの改善が必要です。
*   **エラーハンドリング**:
    ネットワークエラーや予期せぬ応答に対するエラーハンドリングは、さらに強化する余地があります。
*   **セキュリティ**:
    現状、サーバーAPIには認証がありません。必要に応じてAPIキー認証などのセキュリティ対策を検討してください。
*   **Windows Server での `usbip port`**:
    もしサーバーがWindowsの場合、`usbip.exe port` コマンドがクライアントIPや接続バスIDを出力しない可能性があり、その場合は「アプリケーションレベルでの情報管理」に完全に依存することになります。
