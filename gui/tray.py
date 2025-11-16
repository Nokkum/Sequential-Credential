# This is a lightweight system-tray scaffold using pystray. It is optional.
try:
    import pystray
    from PIL import Image, ImageDraw
except Exception:
    pystray = None


def create_image():
    # simple 16x16 icon
    im = Image.new('RGB', (16, 16), 'white')
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 15, 15), fill='black')
    return im


def start_tray(menu_actions: dict):
    if pystray is None:
        return
    icon = pystray.Icon('sequential')
    icon.icon = create_image()
    icon.menu = pystray.Menu(*[pystray.MenuItem(k, v) for k, v in menu_actions.items()])
    icon.run()