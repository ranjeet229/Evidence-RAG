from backend.app.auth import create_token, decode_token, hash_password, verify_password

def test_password_hashes_are_salted_and_verifiable():
    encoded = hash_password('correct horse battery staple')
    assert encoded != 'correct horse battery staple'
    assert verify_password('correct horse battery staple', encoded)
    assert not verify_password('wrong password', encoded)

def test_created_session_carries_user_and_workspace():
    claims = decode_token(create_token('user-1', 'workspace-1'))
    assert claims['sub'] == 'user-1'
    assert claims['workspace_id'] == 'workspace-1'
