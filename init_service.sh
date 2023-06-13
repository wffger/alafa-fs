read -p "请输入端口 (例如： 5000): " PORT
read -p "请输入用户名 (例如： wffger): " ID
read -p "请输入密码 (例如： wffger): " PASSWORD
read -p "请输入文件服务根目录 (例如： /tmp): " ROOT_DIR
WORK_DIR=$(pwd)
WORK_SCRIPT=$WORK_DIR/alafa-fs.py
echo "WORK_SCRIPT is $WORK_SCRIPT"

PORT=${PORT:-5000}
ID=${ID:-wffger}
PASSWORD=${PASSWORD:-wffger}
ROOT_DIR=${ROOT_DIR:-${WORK_DIR}}

mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/alafa-fs.service <<EOL
[Unit]
Description=Alafa File Server
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=on-failure
RestartSec=1
WorkingDirectory=$WORK_DIR
ExecStartPre=
ExecStart=/usr/bin/py $WORK_SCRIPT $PORT $ID:$PASSWORD $ROOT_DIR
ExecStartPost
ExecStop=
ExecReload=

[Install]
WantedBy=default.target
EOL

systemctl --user daemon-reload
systemctl --user enable alafa-fs
systemctl --user start alafa-fs
