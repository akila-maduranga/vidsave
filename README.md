# KeepThisClip

A powerful web-based downloader that downloads files from URLs (up to 2GB) including Instagram, TikTok, Twitter/X, Reddit, Facebook, Vimeo, and 700+ more platforms. Built with Flask, yt-dlp, and Playwright for media extraction.

## Features

- 🌐 **Modern Web Interface** - Clean, responsive UI with glassmorphism design
- 📥 **Multi-Platform Support** - Instagram, TikTok, Twitter/X, Reddit, Facebook, Vimeo + 700+ more
- 🎬 **Quality Selection** - Choose video quality (360p, 480p, 720p, 1080p, Best) before downloading
- 🎵 **Audio Extraction** - Extract audio from videos (MP3)
- ✏️ **Custom Filename** - Rename files before download
- 🔒 **SSL/HTTPS** - Automatic SSL with Caddy and Let's Encrypt
- 🚀 **One-Command Deployment** - Deploy to VPS with a single command
- 📊 **Live Progress** - Real-time download progress tracking
- 🐳 **Docker** - Fully containerized deployment
- 👨‍💼 **Admin Panel** - Built-in admin dashboard for monitoring and configuration
- 📈 **Traffic Analytics** - Track downloads, users, and data transferred
- ⚙️ **Site Configuration** - Customize settings via admin panel

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Caddy (SSL/Proxy)                      │
│                   Port 80/443 (HTTPS)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌──────────────┐  ┌────────────────┐
│ Flask App     │  │  yt-dlp      │  │  MongoDB       │
│ (Web UI)      │  │  (Download)  │  │  (Database)    │
│ Port 8080     │  │  (Built-in)  │  │  Port 27017    │
└───────────────┘  └──────────────┘  └────────────────┘
```

## Quick Start (VPS Deployment)

### Prerequisites

- A VPS with Ubuntu/Debian (recommended: 2GB RAM, 20GB disk)
- A domain name (e.g., keepthisclip.com) pointed to your VPS
- DNS provider (Namecheap, GoDaddy, etc.) - Caddy uses HTTP challenge

### One-Command Deployment

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/keepthisclip.git
cd keepthisclip
```

2. **Configure environment:**
```bash
cp .env.example .env
nano .env
```

Edit the following variables:
```env
DOMAIN=keepthisclip.com
```

3. **Point your domain to your VPS:**
- Go to your DNS provider (Namecheap, GoDaddy, etc.)
- Add an A record pointing to your VPS IP address
- Wait for DNS to propagate (usually 5-30 minutes)

4. **Deploy:**
```bash
chmod +x deploy.sh
./deploy.sh
```

That's it! Your KeepThisClip will be available at `https://keepthisclip.com`

## Manual Deployment

If you prefer manual deployment:

1. **Install Docker and Docker Compose:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Create directories:**
```bash
mkdir -p DOWNLOADS youtube_api/downloads
```

4. **Build and start:**
```bash
docker-compose build
docker-compose up -d
```

## Configuration

### Environment Variables (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| `DOMAIN` | Yes | Your domain name (e.g., keepthisclip.com) |
| `DATABASE_URL` | No | MongoDB connection string (default: mongodb://mongodb:27017/keepthisclip) |
| `FFMPEG_PATH` | No | Path to FFmpeg (default: /usr/bin/ffmpeg) |
| `PORT` | No | Flask app port (default: 8080) |
| `ADMIN_USERNAME` | No | Admin username (default: admin) |
| `ADMIN_PASSWORD` | No | Admin password (default: admin123) |
| `SECRET_KEY` | No | JWT secret key (CHANGE IN PRODUCTION) |

**Note:** Caddy uses HTTP challenge for SSL, which works with any DNS provider (Namecheap, GoDaddy, etc.). No API token needed.

## Usage

1. Open your browser and go to `https://keepthisclip.com`
2. Paste a URL (Instagram, TikTok, Twitter, Facebook, etc.)
3. Click "Analyze URL" to see available qualities
4. Select quality (360p, 480p, 720p, 1080p, Best) and download mode
5. Optionally enter a custom filename
6. Click "Download Now"
7. Wait for download to complete
8. Click "Download File" to save to your device

## Admin Panel

Access the admin panel at `https://keepthisclip.com/admin`

**Default Credentials:**
- Username: `admin`
- Password: `admin123`

⚠️ **Important:** Change the default admin credentials in `.env` before deploying to production.

### Admin Panel Features

**Dashboard:**
- Total users count
- Total downloads
- Data transferred (GB)
- Active downloads

**Users:**
- List of all users/download sessions
- Download count per user
- Last active time
- Active/inactive status

**Traffic:**
- Today's downloads
- Weekly downloads
- Monthly downloads
- Average download size
- Recent downloads list

**Settings:**
- Site name configuration
- Max file size limit
- Download timeout
- Change admin password

## API Endpoints

The web app also provides API endpoints for integration:

### Get Video Formats
```bash
POST /api/formats
Content-Type: application/json

{
  "url": "https://youtube.com/watch?v=xxxx"
}
```

### Start Download
```bash
POST /api/web-download
Content-Type: application/json

{
  "url": "https://youtube.com/watch?v=xxxx",
  "format_id": "best",
  "mode": "direct",
  "filename": "video.mp4"
}
```

Returns:
```json
{
  "download_id": "uuid-string"
}
```

### Check Progress
```bash
GET /api/progress/{download_id}
```

Returns:
```json
{
  "status": "downloading",
  "percentage": 45.5,
  "action": "Downloading...",
  "speed": "5.2 MB/s"
}
```

### Download File
```bash
GET /api/download-file/{download_id}
```

### Link Extraction API
```bash
GET /grab?url={url}
POST /grab
Content-Type: application/json
{"url": "https://example.com/video"}
```

## Management Commands

### View logs:
```bash
docker-compose logs -f
```

### Stop services:
```bash
docker-compose down
```

### Restart services:
```bash
docker-compose restart
```

### Update and rebuild:
```bash
git pull
docker-compose build
docker-compose up -d
```

### Clean up old downloads:
```bash
docker-compose exec app rm -rf /app/DOWNLOADS/*
```

## Troubleshooting

### SSL not working?
- Check that your domain DNS points to your VPS
- Verify DNS has propagated (5-30 minutes)
- Check Caddy logs: `docker-compose logs caddy`

### Downloads failing?
- Check app logs: `docker-compose logs app`
- Verify YouTube API is running: `docker-compose logs youtube-api`
- Check disk space: `df -h`

### Port 80/443 already in use?
- Stop other web servers (nginx, apache)
- Or modify Caddyfile to use different ports

### Admin panel not accessible?
- Verify admin credentials in .env
- Check app logs for authentication errors
- Ensure SECRET_KEY is set

## Local Development

### Prerequisites

- Python 3.11+
- FFmpeg
- MongoDB (optional - can skip for testing)

### Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install FFmpeg
# Windows: Download from https://ffmpeg.org/download.html
# Mac: brew install ffmpeg
# Linux: sudo apt install ffmpeg

# Install Playwright browsers
playwright install chromium

# Set environment variables
export DOMAIN=localhost
export PORT=8080

# Run the web app
python app_web.py
```

Then open `http://localhost:8080` in your browser.

## Security

- All downloads are isolated in Docker containers
- Automatic SSL with Let's Encrypt
- URL validation to prevent SSRF attacks
- Old downloads are automatically cleaned up (1 hour)
- Admin panel protected with JWT tokens (24-hour expiration)
- Change default credentials before production

## Supported Platforms

yt-dlp supports 1700+ sites including:
- Instagram
- TikTok
- Twitter/X
- Facebook
- Reddit
- Vimeo
- Dailymotion
- Twitch
- SoundCloud
- Bilibili
- And many more...

## Project Structure

```
keepthisclip/
├── app_web.py              # Flask web server
├── docker-compose.yml      # Docker orchestration
├── Dockerfile.web          # Web Dockerfile
├── Caddyfile              # Caddy SSL configuration
├── deploy.sh              # One-command deployment script
├── .env.example           # Environment variables template
├── requirements.txt       # Python dependencies
├── plugins/
│   ├── config.py          # Configuration
│   └── helper/
│       ├── upload.py      # Download logic (yt-dlp)
│       ├── extractor.py   # Link extraction
│       └── database.py    # MongoDB operations
└── web_new/
    ├── index.html         # Main web UI
    ├── app.js            # Frontend JavaScript
    └── admin.html        # Admin panel
```

## License

This project is based on the Telegram URL Uploader Bot, transformed into a web application.

## Credits

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video downloader
- [Playwright](https://playwright.dev/) - Browser automation
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Caddy](https://caddyserver.com/) - Web server with automatic SSL
- [Docker](https://www.docker.com/) - Containerization
