from __future__ import annotations


def pad_expression(style: str, amount: float, duration: float) -> tuple[str, str]:
    amount = max(0.0, min(float(amount), 24.0))
    duration = max(float(duration), 0.1)
    if style == "float":
        return (
            f"(ow-iw)/2+{amount:.2f}*sin(2*PI*t/{duration:.3f})",
            f"(oh-ih)/2+{amount:.2f}*cos(2*PI*t/{duration:.3f})",
        )
    if style == "pan":
        return (
            f"(ow-iw)*t/{duration:.3f}",
            f"(oh-ih)*(1-t/{duration:.3f})",
        )
    return "(ow-iw)/2", "(oh-ih)/2"
