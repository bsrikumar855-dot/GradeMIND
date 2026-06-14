import cv2
import numpy as np
import os

input_path = r'C:\Users\DELL\.gemini\antigravity-ide\brain\47c1865a-ede0-41cb-916b-91f19a9a5749\media__1781280994263.jpg'
output_dir = r'C:\Users\DELL\OneDrive\Desktop\GM\src\public\images\logo'

# Load image
img = cv2.imread(input_path)
if img is None:
    print(f"Could not load image at {input_path}")
    exit(1)

# Convert to grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Threshold to separate bright gold from dark green
# The gold is quite bright, green is dark.
_, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)

# Clean up mask
kernel = np.ones((3,3), np.uint8)
thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

# To make a clean solid logo, we can find contours and draw them
contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

mask = np.zeros_like(gray)
# Draw all significant contours
for cnt in contours:
    if cv2.contourArea(cnt) > 50: # filter out noise
        cv2.drawContours(mask, [cnt], 0, 255, -1)

# However, the logo has holes (the brain folds). RETR_TREE returns hierarchy.
# Actually, just using the thresholded mask directly after some smoothing might be better to preserve the intricate lines.
# Let's smooth the mask using GaussianBlur and threshold again for anti-aliasing effect
blurred = cv2.GaussianBlur(thresh, (5, 5), 0)
_, mask_aa = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)

# Now we have a clean mask of the logo.
# Let's crop to the bounding box of the logo to remove empty space.
coords = cv2.findNonZero(mask_aa)
x, y, w, h = cv2.boundingRect(coords)
logo_mask = mask_aa[y:y+h, x:x+w]

# Function to create a colored version
def create_colored_logo(mask, hex_color):
    # hex_color is string like '#2F5A3A'
    h = hex_color.lstrip('#')
    rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    bgr = (rgb[2], rgb[1], rgb[0])
    
    # Create an image of the required color
    colored = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
    colored[:,:,0] = bgr[0]
    colored[:,:,1] = bgr[1]
    colored[:,:,2] = bgr[2]
    colored[:,:,3] = mask # Alpha channel is the mask itself
    
    return colored

colors = {
    'primary': '#2F5A3A',
    'secondary': '#86B77B',
    'light': '#FFFDF8',
    'accent': '#5B8DEF'
}

# 1. Full-color logo: Primary Green (#2F5A3A)
full_color = create_colored_logo(logo_mask, colors['primary'])
cv2.imwrite(os.path.join(output_dir, 'logo-full-color.png'), full_color)

# 2. Monochrome dark: #2F5A3A
cv2.imwrite(os.path.join(output_dir, 'logo-dark.png'), full_color) # Same as full color in this flat vector conversion

# 3. Monochrome light: #FFFDF8
light_color = create_colored_logo(logo_mask, colors['light'])
cv2.imwrite(os.path.join(output_dir, 'logo-light.png'), light_color)

# 4. Navbar version: Resize height to 32px
aspect_ratio = logo_mask.shape[1] / logo_mask.shape[0]
nav_h = 32
nav_w = int(nav_h * aspect_ratio)
nav_logo = cv2.resize(full_color, (nav_w, nav_h), interpolation=cv2.INTER_AREA)
cv2.imwrite(os.path.join(output_dir, 'logo-navbar.png'), nav_logo)

# 5. Sidebar version: Resize to something suitable, e.g., 64x64
side_h = 64
side_w = int(side_h * aspect_ratio)
side_logo = cv2.resize(full_color, (side_w, side_h), interpolation=cv2.INTER_AREA)
cv2.imwrite(os.path.join(output_dir, 'logo-sidebar.png'), side_logo)

# 6. Favicon version: 32x32 padded to square
fav_size = 32
favicon = np.zeros((fav_size, fav_size, 4), dtype=np.uint8)
if nav_w <= fav_size:
    offset = (fav_size - nav_w) // 2
    favicon[:, offset:offset+nav_w] = nav_logo
else:
    # If width > 32, resize based on width instead
    fav_w = 32
    fav_h = int(fav_w / aspect_ratio)
    fav_logo = cv2.resize(full_color, (fav_w, fav_h), interpolation=cv2.INTER_AREA)
    offset = (fav_size - fav_h) // 2
    favicon[offset:offset+fav_h, :] = fav_logo

cv2.imwrite(os.path.join(output_dir, 'favicon.png'), favicon)

print("Successfully generated all logo variations.")
