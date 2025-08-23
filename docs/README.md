# 🎥 ThemeQR – QR Codes That Entertain

ThemeQR is a dynamic web app that lets users generate custom QR codes wrapped in themed video or image overlays. Each QR code links to a landing page that can be updated at any time, making it perfect for marketing, events, birthdays, and more.

---

## 📌 Features

- 🎥 **Video Wrappers**: Wrap QR codes with funny, stylish, or branded MP4s.
- 🔁 **Dynamic Landing Pages**: Change QR destination even after it’s printed.
- 📁 **TQR Vault**: Store and manage your custom QR decks.
- 🌐 **Cloud-based Delivery**: Host assets on Cloudinary and landing pages on GitHub Pages or Vercel.
- 🛠️ **Supabase Integration**: Store users, decks, and themes with row-level security.

---

## 🧰 Tech Stack

| Layer       | Tech Used                   |
|-------------|-----------------------------|
| Frontend    | HTML, CSS, JavaScript       |
| Backend     | Python (Flask)              |
| Database    | Supabase (PostgreSQL)       |
| Hosting     | GitHub Pages / Vercel       |
| Media CDN   | Cloudinary                  |
| QR Code Gen | Python `qrcode`, Pillow     |
| Video       | MoviePy                     |

---

## 🗂 Project Structure

hemeqr/
├── app.py # Flask app backend
├── templates/
│ └── index.html
│ └── editor.html
├── static/
│ └── (wrapper videos, QR images)
├── theme/
│ └── theme_name/
│ ├── wrapper.mp4
│ └── landing_url.txt
├── vault/
│ └── decks/
│ └── deck_name/
│ ├── wrapper.mp4
│ ├── qr.png
│ └── landing_url.txt
├── birthday_deck_builder.py # Script to create video + QR
└── .env # Cloudinary & Supabase credentials


---

## 🚀 Setup Guide

### 1. Clone the Repo

```bash
git clone https://github.com/bdkelmon/themeqr.git
cd themeqr

python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_key
CLOUDINARY_API_SECRET=your_secret
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_or_service_key

python app.py
Visit: http://localhost:5000

🧪 Generate a QR Video Deck
Exanple usage`
python birthday_deck_builder.py https://yourpage.com/landing.html "./BirthdayParty.mp4

This will generate:

A QR code image

A new video with the QR overlay

Upload both to Cloudinary

Print out the secure URLs

🔐 Supabase Setup
Create tables: users, qr_decks, qr_codes

Add foreign keys (user_id, deck_id)

Enable Row Level Security (RLS)

Add policies:

user_id = auth.uid() for SELECT/UPDATE on qr_decks

deck_id in (SELECT id FROM qr_decks WHERE user_id = auth.uid()) for qr_codes

✨ Future Features
User authentication (Supabase)

Web UI deck editor

Theme marketplace

Analytics tracking

👤 Author
Built by @bdkelmon

📄 License
See License.txt


