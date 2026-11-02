import pytest
from app.config.validate_security_config import validate_security_config
from app import create_app

#unit tests

def test_empty_key():
    key = ''
    with pytest.raises(ValueError, match='Config Error missing key'):        
        validate_security_config(key)

def test_no_key():
    
    key = None
    with pytest.raises(ValueError,match='Config Error missing key'):        
        validate_security_config(key)

def test_short_key():
    
    key = 'short_key'
    with pytest.raises(ValueError, match='Config Error short key'):        
        validate_security_config(key)

def test_right_key():
    key = 'long_key_asddasdasdafsgwrertdbcvxbxrgwrwaerqWEQewqrsfsdkgldngkadnglk'
    validate_security_config(key)


#Integration tests

def test_factory_accepts_valid_key():
    test_key = "this-is-only-a-test-key-with-enough-length-12345"

    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": test_key,
    })

    assert app.config["JWT_SECRET_KEY"] == test_key    

def test_factory_rejects_short_key():
    with pytest.raises(ValueError, match="Config Error short key"):
        create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "JWT_SECRET_KEY": "short",
        })
def test_factory_rejects_no_key():
    with pytest.raises(ValueError, match="Config Error missing key"):
        create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "JWT_SECRET_KEY": None,
        })