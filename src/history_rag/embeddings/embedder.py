import time
import httpx
from rich.console import Console
from rich.progress import Progress

console = Console()

DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"


def _get_batch_size(model_name: str) -> int:
    """v3 supports 25 per request, v4 only 10."""
    if "v3" in model_name or "v2" in model_name or "v1" in model_name:
        return 25
    return 10


class Embedder:
    def __init__(self, model_name: str = "text-embedding-v3", provider: str = "dashscope", api_key: str = ""):
        self.model_name = model_name
        self.provider = provider
        self.api_key = api_key
        self.batch_size = _get_batch_size(model_name) if provider == "dashscope" else 64

        if provider == "local":
            import torch
            from sentence_transformers import SentenceTransformer
            console.print(f"[yellow]加载本地模型: {model_name}...[/yellow]")
            self.local_model = SentenceTransformer(model_name)
            console.print("[green]模型加载完成[/green]")
        else:
            console.print(f"[green]使用 DashScope API: {model_name} (batch_size={self.batch_size})[/green]")

    def _call_dashscope(self, texts: list[str], retries: int = 3) -> list[list[float]]:
        """Call DashScope embedding API with retry."""
        cleaned = []
        for t in texts:
            t = t[:3000] if len(t) > 3000 else t
            t = t.strip() if t.strip() else "空"
            cleaned.append(t)

        for attempt in range(retries):
            try:
                resp = httpx.post(
                    DASHSCOPE_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model_name,
                        "input": cleaned,
                        "encoding_format": "float",
                    },
                    timeout=120,
                )
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    console.print(f"[yellow]速率限制，等待 {wait}s...[/yellow]")
                    time.sleep(wait)
                    continue
                if resp.status_code != 200:
                    console.print(f"[red]API 错误 {resp.status_code}: {resp.text[:200]}[/red]")
                    if attempt < retries - 1:
                        time.sleep(1)
                        continue
                resp.raise_for_status()
                data = resp.json()
                sorted_data = sorted(data["data"], key=lambda x: x["index"])
                return [item["embedding"] for item in sorted_data]
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt < retries - 1:
                    wait = 2 ** (attempt + 1)
                    console.print(f"[yellow]网络错误({type(e).__name__})，{wait}s 后重试 {attempt + 1}/{retries}...[/yellow]")
                    time.sleep(wait)
                    continue
                raise

        raise RuntimeError("DashScope API 调用失败")

    def embed(self, texts: list[str], batch_size: int | None = None) -> list[list[float]]:
        if self.provider == "local":
            import torch
            with torch.no_grad():
                embeddings = self.local_model.encode(
                    texts, batch_size=64, normalize_embeddings=True, show_progress_bar=True,
                )
            return embeddings.tolist()

        bs = batch_size or self.batch_size
        all_embeddings = []
        with Progress() as progress:
            task = progress.add_task("嵌入中...", total=len(texts))
            for i in range(0, len(texts), bs):
                batch = texts[i:i + bs]
                embeddings = self._call_dashscope(batch)
                all_embeddings.extend(embeddings)
                progress.update(task, advance=len(batch))

        return all_embeddings

    def embed_query(self, query: str) -> list[float]:
        if self.provider == "local":
            import torch
            with torch.no_grad():
                embedding = self.local_model.encode([query], normalize_embeddings=True)
            return embedding[0].tolist()

        return self._call_dashscope([query])[0]
