# AI Code Reviewer

An AI-powered code review application built with Streamlit, Gemini API, and Resend API. The application analyzes source code, provides intelligent suggestions for improvement, and can email the review results.

## Features

- AI-powered code analysis
- Code quality improvement suggestions
- Error detection and optimization recommendations
- Email code review reports using Resend API
- Interactive web interface built with Streamlit

## Technologies Used

- Python
- Streamlit
- Gemini API
- Resend API
- HTML
- CSS

## Project Structure

```
app.py
main.py
codeware.db
```

## Installation

1. Clone the repository

```bash
git clone https://github.com/ushripaul/AICodeReviewer.git
```

2. Move into the project directory

```bash
cd AICodeReviewer
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Add your API keys

```
GEMINI_API_KEY=your_key
RESEND_API_KEY=your_key
```

5. Run the application

```bash
streamlit run app.py
```

## Future Enhancements

- Support multiple programming languages
- Generate downloadable PDF reports
- User authentication
- Code history management
