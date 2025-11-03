<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/drive/1AQVbISjAT414ZCDfbSO7EQ9BFfmpg-EV

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local) to your Gemini API key
3. Run the app:
   `npm run dev`

## Integrate With The Bot

1. Build the mini-app for production with `npm run build`. The compiled assets will appear in `store-mini-app/dist`.
2. Host the contents of `dist` on an HTTPS endpoint accessible from Telegram (for example, via a static hosting service or your own web server).
3. Set the HTTPS address in the bot's environment variable `SHOP_WEB_APP_URL`. The bot reads this value from `.env`.
4. Restart the bot container or process. Tapping the shop button in Telegram will now open the hosted mini-app, and confirmed orders are forwarded to the bot as web app data.
