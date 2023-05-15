import registration_api


x = registration_api.API()

token = x.register("jvadair", "jva@jvadair.com", "password")
assert len(registration_api.unverified.where(username="jvadair")) > 0
x.verify(token)
assert len(registration_api.unverified.where(username="jvadair")) == 0
session = {}
resp = x.login(session, "jvadair", "password")
pass
