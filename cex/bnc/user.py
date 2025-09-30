from dataclasses import dataclass


@dataclass
class UserCfg:
    api_key: str
    api_secret_key: str


class User:
    def __init__(self, cfg: UserCfg):
        self.cfg = cfg

    def new_listen_key(self, url: str) -> tuple[str, Exception | None]:
        return "", None

    def keep_listen_key(self, url: str, listen_key: str) -> tuple[str, Exception | None]:
        return "", None
