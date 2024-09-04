cat <<EOF >/etc/systemd/system/nineteen-autoupdater.service
[Unit]
Description=Validator AutoUpdater
After=network.target
StartLimitIntervalSec=30
StartLimitBurst=2

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$HOME/nineteen
ExecStart=python -u run_validator_auto_update.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# load it and start
systemctl daemon-reload
systemctl enable --now nineteen-autoupdater
systemctl restart nineteen-autoupdater