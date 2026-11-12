from fastapi import FastAPI, HTTPException

from app.generative import HermesProviderError, ModelOutputError, analyze_generative
from app.rules import classify_traditional
from app.schemas import AnalysisResult, AnalyzeRequest, Mode


app = FastAPI(
    title="AI Support Engine",
    version="0.1.0",
    description="Clasifica solicitudes de soporte con reglas o con el modelo de Hermes.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze", response_model=AnalysisResult, response_model_by_alias=True)
def analyze(request: AnalyzeRequest) -> AnalysisResult:
    if request.mode is Mode.TRADITIONAL:
        return classify_traditional(request.message)

    try:
        return analyze_generative(request.message)
    except (HermesProviderError, ModelOutputError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    except Exception:
        # Do not leak upstream payloads, credentials, or stack traces to API clients.
        raise HTTPException(
            status_code=502,
            detail="No fue posible obtener una respuesta válida del modelo generativo.",
        ) from None
