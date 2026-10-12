from backend.app.services import keywords
def test_keywords_exclude_common_question_words():
 assert keywords('What is the salary mentioned in this file?')=={'salary','mentioned'}
