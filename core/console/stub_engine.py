from pathlib import Path


class StubEngine:
    def __init__(self, custom_stubs_dir: str | None = None) -> None:
        self._builtin_dir = Path(__file__).parent / "stubs"
        self._custom_dir = Path(custom_stubs_dir) if custom_stubs_dir else None

    def render(self, stub_name: str, variables: dict[str, str]) -> str:
        content = self._load(stub_name)
        for key, value in variables.items():
            content = content.replace(f"{{{{ {key} }}}}", value)
            content = content.replace(f"{{{{{key}}}}}", value)
        return content

    def generate(self, stub_name: str, output_path: str, variables: dict[str, str]) -> str:
        content = self.render(stub_name, variables)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path.resolve())

    def _load(self, stub_name: str) -> str:
        if not stub_name.endswith(".stub"):
            stub_name += ".stub"

        if self._custom_dir:
            custom_path = self._custom_dir / stub_name
            if custom_path.exists():
                return custom_path.read_text(encoding="utf-8")

        builtin_path = self._builtin_dir / stub_name
        if builtin_path.exists():
            return builtin_path.read_text(encoding="utf-8")

        raise FileNotFoundError(f"Stub '{stub_name}' not found")

    def stub_exists(self, stub_name: str) -> bool:
        if not stub_name.endswith(".stub"):
            stub_name += ".stub"
        if self._custom_dir and (self._custom_dir / stub_name).exists():
            return True
        return (self._builtin_dir / stub_name).exists()
