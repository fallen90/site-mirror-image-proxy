import io
import re
import os
import textwrap
import requests
from pathlib import Path
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, request, Response, make_response, send_file

app = Flask(__name__)
CORS(app)

# Get the base directory from the environment variable, defaulting to '/mnt/local-usb/MangaCollection'
base_directory = os.getenv('MANGA_COLLECTION_DIRECTORY', '/mnt/local-usb/MangaCollection')


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Get manga_id and chapter_id from the request
        manga_id = request.form.get('manga_id')
        chapter_id = request.form.get('chapter_id')

        # Get the filename from the request
        filename = request.form.get('filename')

        # Check if manga_id, chapter_id, and filename are provided
        if not manga_id or not chapter_id or not filename:
            print(f"manga_id: {manga_id}")
            print(f"chapter_id: {chapter_id}")
            print(f"filename: {filename}")
            return Response('Manga_id, chapter_id, and filename are required', status=400, content_type='text/plain')

        # Determine the directory based on manga_id
        if manga_id == 'cover':
            directory = os.path.join(base_directory, 'cover-images')
        else:
            directory = os.path.join(base_directory, manga_id, chapter_id)

        Path(directory).mkdir(parents=True, exist_ok=True)

        # Get the file buffer from the request
        file_buffer = request.files['file'].read()

        # Save the file to the specified directory with the given filename
        file_path = os.path.join(directory, filename)
        with open(file_path, 'wb') as file:
            file.write(file_buffer)

        return 'File saved successfully', 200

    except Exception as e:
        return f'Error: {str(e)}', 500


@app.route('/download', methods=['GET'])
def download_file():
    try:
        # Get the URL from the query parameter
        url = request.args.get('url')
        fallback_url = request.args.get('fallback_url', url)  # Use fallback_url if provided, else use the original url

        quality = int(request.args.get('quality', 95))
        type = request.args.get('type', 'page')

        print(f"url={url}")

        # Check if the URL is provided
        if not url:
            # Return an image with "Image not Found" text
            return generate_not_found_image(text="Image not Found / Invalid URL")

        # Extract manga_id and chapter_id using regex
        match = re.match(r'.*/(?P<manga_id>manga_[a-z0-9]+)\/(?P<chapter_id>[a-z0-9]+)\/', url, re.IGNORECASE)
        manga_id = ""
        chapter_id = ""
        

        if match is not None:
            manga_id = match.group('manga_id')
            chapter_id = match.group('chapter_id')
        elif type == 'cover':
            cover_match = re.search(r'(-\d{1,4}x\d{1,4})\.jpg$', url)
            if cover_match:
                url = url.replace(cover_match.group(1), '')
                print(url)
        else:
            return generate_not_found_image(text="Invalid URL Format")

        directory = ""
        if type == 'cover':
            directory = os.path.join(base_directory, 'cover-images')
        else:
            directory = os.path.join(base_directory, manga_id, chapter_id)
            
        # create dir if not exists
        Path(directory).mkdir(parents=True, exist_ok=True)

        # Get the filename from the URL
        filename = url.split('/')[-1]

        # Check if the file exists in the specified directory
        file_path = os.path.join(directory, filename)
        if os.path.exists(file_path):
            # Process the image and return it with appropriate headers for display
            img_io = process_image(file_path, quality)
            return send_file(img_io, download_name=filename, mimetype='image/jpeg')
        else:
            # File doesn't exist, download it using the fallback URL
            for current_url in [url, fallback_url]:
                result = download_and_process_image(current_url, file_path, fallback_url, quality)
                if result:
                    return result

            # If both URLs fail, return an error response
            return generate_not_found_image(text=f"Failed to download file from {fallback_url}")

    except Exception as e:
        return f'Error: {str(e)}', 500
    
def generate_not_found_image(text=""):
    # Create an image with gray background and the specified text
    width, height = 400, 800
    background_color = (192, 192, 192)  # RGB values for gray
    text_color = (0, 0, 0)  # RGB values for black

    image = Image.new('RGB', (width, height), background_color)
    draw = ImageDraw.Draw(image)

    # Use a font size that fits within the specified width
    font_size = 30
    font = ImageFont.load_default(size=font_size)  # Using default font
    
    # Wrap the text using textwrap.wrap
    wrapped_lines = textwrap.wrap(text, width=20)  # Adjust the width as needed

    # Calculate position to center the text vertically
    y = (height - draw.textbbox((0, 0), wrapped_lines[0], font=font)[3] * len(wrapped_lines)) // 2

    # Draw the centered text horizontally
    for line in wrapped_lines:
        text_bbox = draw.textbbox((0, 0), line, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        x = (width - text_width) // 2
        draw.text((x, y), line, font=font, fill=text_color)
        y += text_bbox[3] - text_bbox[1]

    # Save the image to a buffer
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    buffer.seek(0)

    # Return the image as a response
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'image/jpeg'
    return response

def process_image(file_path, quality):
    img = Image.open(file_path)
    img_io = io.BytesIO()
    img.save(img_io, format='JPEG', quality=quality)
    img_io.seek(0)
    return img_io

def download_and_process_image(url, file_path, fallback_url, quality):
    response = requests.get(url)

    if response.status_code == 200:
        # Save the file to the specified directory with the given filename
        with open(file_path, 'wb') as file:
            file.write(response.content)

        # Process the image and return it with appropriate headers for display
        img_io = process_image(file_path, quality)
        return send_file(img_io, download_name=os.path.basename(file_path), mimetype='image/jpeg')

    return None


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)