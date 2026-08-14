"""QR de inscripción al curso, en el índigo del deck.

Sin logo al centro: es un QR de acción (se escanea desde el fondo de la sala),
no una tarjeta de identidad. Menos elementos = decodifica más lejos.
Se verifica DECODIFICANDO, nunca mirándolo.
"""
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask

URL = "https://datahackers.ai/curso/databricks-ai-engineer"
INDIGO = (83, 58, 253)   # --primary del deck
BLANCO = (255, 255, 255)
SALIDA = "qr-curso.png"


def build(nombre=SALIDA, fill=INDIGO, back=BLANCO):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=30,
        border=4,  # quiet zone mínima del estándar
    )
    qr.add_data(URL)
    qr.make(fit=True)
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(radius_ratio=1),
        color_mask=SolidFillColorMask(front_color=fill, back_color=back),
    ).convert("RGB").resize((1400, 1400))
    img.save(nombre)
    print(f"{nombre}  1400px  módulos={qr.modules_count}")


if __name__ == "__main__":
    build()
