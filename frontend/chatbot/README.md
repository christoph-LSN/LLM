# AI Chatbot Widget Templates

This project contains a collection of templates for AI chatbot widgets.

## Project Structure
- `frontend/`: Contains all the frontend related files.
- `backend/`: Contains server-side logic.
- `training_data.json`: Holds training data used for AI training.

## File Descriptions
- `README.md`: Overview of the project.
- `index.html`: Main entry point for the chatbot widget.
- `chatbot.js`: Core functionality of the AI chatbot.
- `styles.css`: Styling for the chatbot widget.

## Quick Start
1. Clone the repository: `git clone https://github.com/christoph-LSN/LLM.git`
2. Navigate to the `frontend/chatbot` directory.
3. Open `index.html` in your browser.

## Configuration Options
- `apiKey`: Your API key for accessing services.
- `botName`: The default name of the chatbot.

## Feature Flag Mechanism
You can control feature flags in the `config.js` file within the `frontend/` directory. This helps enable or disable features during development.

## Development vs Production Modes
- **Development mode**: Use `dev` configurations for testing and debugging.
- **Production mode**: Use `prod` configurations for actual deployment to ensure performance and security.

## Links to Data
- [training_data.json](../training_data.json): Link to the training data file used by the chatbot.