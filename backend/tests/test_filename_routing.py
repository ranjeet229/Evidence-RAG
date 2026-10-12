from backend.app.services import keywords
def test_filename_words_are_meaningful_retrieval_terms():
 assert keywords('What is the salary in salary slip file')=={'salary','slip'}
