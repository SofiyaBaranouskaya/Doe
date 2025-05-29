from PIL import Image, ImageDraw
from io import BytesIO

def generate_initial_avatar(user):
    img = Image.new('RGB', (300, 300), color=(255, 200, 200))
    draw = ImageDraw.Draw(img)
    draw.text((75, 130), user.first_name[0].upper(), fill='black')

    output = BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    return output