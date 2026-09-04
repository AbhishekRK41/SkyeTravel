# HydraLoop 💧

A habit-forming water intake tracker that adapts its hydration targets to your body weight and daily needs — built as a React + TypeScript progressive web app.

## Features

- Personalized daily hydration goal based on body weight
- Habit-tracking loop to log and visualize intake over time
- Installable as a PWA via a service worker (works offline, add-to-homescreen)
- Dark-themed, mobile-first UI built with Tailwind CSS

## Tech stack

- **React 18** + **TypeScript**
- **Vite** for dev server and build
- **Tailwind CSS** for styling
- Service worker for offline/PWA support

## Setup

**Requirements:** Node.js 18+

```bash
git clone https://github.com/AbhishekRK41/HydraLoop-Final.git
cd HydraLoop-Final
npm install
```

## Usage

```bash
npm run dev       # start the dev server
npm run build      # production build
npm run preview    # preview the production build locally
```

## Architecture

```
src/
├── App.tsx          # root component, routing/state
├── main.tsx          # React entry point
└── index.css          # Tailwind entry styles
public/                # static assets
service-worker.js       # PWA offline support
```

## Roadmap / ideas

- Push notification reminders for hydration check-ins
- Sync history across devices
