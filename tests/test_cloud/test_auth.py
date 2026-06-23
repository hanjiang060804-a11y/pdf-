from pdf_tra.cloud.auth import create_token, mask_openid, verify_token
from pdf_tra.cloud.settings import CloudSettings


def test_jwt_roundtrip():
    settings = CloudSettings(
        wechat_app_id="a",
        wechat_app_secret="b",
        jwt_secret="roundtrip-secret-key-32chars!!!!",
        dev_mode=True,
    )
    token = create_token(settings, "user-openid-123")
    assert verify_token(settings, token) == "user-openid-123"


def test_mask_openid():
    assert mask_openid("dev-openid") == "dev-****enid"
