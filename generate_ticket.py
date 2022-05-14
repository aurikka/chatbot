from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

TEMPLATE_PATH = "files/conf_ticket.png"
FONT_PATH = "files/Roboto-Regular.ttf"
TEMPLATE_AVIA = 'files/avia_ticket_empty.jpg'
FONT_SIZE = 25
AVATAR_SIZE = 100

BLACK = (0, 0, 0, 255)

NAME_OFFSET = (224, 220)
EMAIL_OFFSET = (224, 245)
AVATAR_OFFSET = (60, 200)


def generate_ticket(name, email):
    base = Image.open(TEMPLATE_PATH)
    fnt = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    draw = ImageDraw.Draw(base)
    draw.text(NAME_OFFSET, name, font=fnt, fill=BLACK)
    draw.text(EMAIL_OFFSET, email, font=fnt, fill=BLACK)

    avatar = Image.open('files/avatar_pr.png')
    base.paste(avatar, AVATAR_OFFSET)
    temp_file = BytesIO()
    base.save(temp_file, 'png')
    temp_file.seek(0)
    return temp_file


def generate_avia_ticket(from_, to_, date):
    base = Image.open(TEMPLATE_AVIA)
    fnt = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    draw = ImageDraw.Draw(base)
    flight_time = (160, 210)
    draw.text(flight_time, date, font=fnt, fill=BLACK)
    draw_from = (160, 400)
    draw.text(draw_from, from_, font=fnt, fill=BLACK)
    draw_to = (650, 400)
    draw.text(draw_to, to_, font=fnt, fill=BLACK)
    temp_file = BytesIO()
    base.save(temp_file, 'png')
    temp_file.seek(0)
    return temp_file


if __name__ == "__main__":
    generate_avia_ticket('Москва', 'Екатеринбург', '2020-12-28 в 17-25')

