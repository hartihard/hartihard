#!/usr/bin/env bash
# KI Hub – Installations-Skript
# Installiert den 'videoload' Terminal-Befehl und die Desktop-App

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   KI Hub – Video Downloader Install  ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo ""

# 1) yt-dlp installieren
echo -e "${YELLOW}[1/4] Installiere yt-dlp und Flask...${NC}"
pip3 install --user yt-dlp flask -q
echo -e "${GREEN}      ✓ Pakete installiert${NC}"

# 2) videoload Befehl anlegen
echo -e "${YELLOW}[2/4] Erstelle 'videoload' Terminal-Befehl...${NC}"
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/videoload" << EOF
#!/usr/bin/env bash
python3 "$SCRIPT_DIR/cli.py" "\$@"
EOF
chmod +x "$HOME/.local/bin/videoload"
echo -e "${GREEN}      ✓ videoload Befehl erstellt${NC}"

# 3) Desktop-App Eintrag erstellen
echo -e "${YELLOW}[3/4] Erstelle Desktop-App Eintrag...${NC}"
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/kihub-downloader.desktop" << EOF
[Desktop Entry]
Name=KI Hub – Video Downloader
Comment=Videos herunterladen fur ComfyUI, Fooocus und mehr
Exec=python3 $SCRIPT_DIR/gui.py
Icon=applications-multimedia
Terminal=false
Type=Application
Categories=AudioVideo;Video;
Keywords=video;download;youtube;tiktok;comfyui;fooocus;
StartupNotify=true
EOF
chmod +x "$HOME/.local/share/applications/kihub-downloader.desktop"
echo -e "${GREEN}      ✓ Desktop-App erstellt${NC}"

# 4) PATH pruefen
echo -e "${YELLOW}[4/4] Prufe PATH...${NC}"
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "" >> "$HOME/.bashrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo "" >> "$HOME/.zshrc" 2>/dev/null || true
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc" 2>/dev/null || true
    echo -e "${GREEN}      ✓ PATH erweitert (bitte Terminal neu starten)${NC}"
else
    echo -e "${GREEN}      ✓ PATH bereits korrekt${NC}"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Installation abgeschlossen!        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}Terminal-Befehl:${NC}"
echo -e "    videoload <URL>                     # in ~/Videos/Downloads"
echo -e "    videoload <URL> --ziel comfyui      # in ComfyUI/input/"
echo -e "    videoload <URL> --ziel fooocus      # in Fooocus/inputs/"
echo -e "    videoload <URL> --qualitaet audio   # nur MP3"
echo ""
echo -e "  ${CYAN}Desktop App:${NC}"
echo -e "    python3 $SCRIPT_DIR/gui.py"
echo -e "    oder im App-Menu: 'KI Hub – Video Downloader'"
echo ""
echo -e "  ${CYAN}Web App (Browser):${NC}"
echo -e "    python3 $SCRIPT_DIR/app.py  →  http://localhost:5000"
echo ""
