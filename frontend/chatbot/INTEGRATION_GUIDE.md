# Integration Guide

## 1) How to Copy Files to MT_Site Repo
- Clone the `MT_Site` repository to your local machine:
  ```bash
  git clone <repo-url-of-MT_Site>
  ```
- Copy the necessary files from the `LLM` repository to the `MT_Site` directory:
  ```bash
  cp -r path/to/files MT_Site/path/to/destination
  ```
- Commit and push the changes:
  ```bash
  cd MT_Site
  git add .
  git commit -m "Add files from LLM"
  git push origin main
  ```

## 2) How to Update _layouts/default.html with the Chatbot Include
- Open the `_layouts/default.html` file in the `MT_Site` repository:
  ```bash
  nano MT_Site/_layouts/default.html
  ```
- Insert the following line where you want to include the chatbot:
  ```html
  {% include chatbot.html %}
  ```
- Save the file and exit.

## 3) How to Test in Development Mode
- Make sure you have all required dependencies installed:
  ```bash
  bundle install
  ```
- Run the server in development mode:
  ```bash
  bundle exec jekyll serve
  ```
- Open your browser and navigate to `http://localhost:4000` to see the changes.

## 4) How to Deploy in Production Mode with Proper Config Overrides
- Build the site for production:
  ```bash
  bundle exec jekyll build --config _config.yml,_config.production.yml
  ```
- Deploy the `_site` folder to your web server or hosting service.

## 5) Troubleshooting Tips
- If you encounter errors during build:
  - Check the error message for missing assets or gems.
  - Ensure all paths in your HTML files are correct.
- Consult the Jekyll documentation for specific error messages.

## 6) Feature Flag Management
- Create a feature flag in your codebase by using environment variables:
  ```bash
  export FEATURE_NAME=true
  ```
- Use conditional statements in your code to trigger features based on the flag status.