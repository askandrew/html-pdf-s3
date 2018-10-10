import boto3
import time
import os
from xhtml2pdf import pisa

print('Loading function')

time_str = str(time.strftime("%Y%m%d-%H%M%S"))


def custom_exception(e):
    exception_type = e.__class__.__name__
    exception_message = e.message
    response = dict()

    api_exception_obj = {
        "type": exception_type,
        "description": exception_message
    }
    response['file_url'] = ""
    response['code'] = "01"
    response['message'] = api_exception_obj

    return response


def generate_pdf(html, option):
    # Set variable
    orientation = "potrait" if "orientation" in option and option['orientation'] =="P" else "landscape"
    measure_unit = option['measure_unit'] if "measure_unit" in option else "mm"
    page_size = option['page_size'] if "page_size" in option else "A4"
    margin_left = str(option['margin_left']) if "margin_left" in option else "1"
    margin_top = str(option['margin_top']) if "margin_top" in option else "1"
    margin_right = str(option['margin_right']) if "margin_right" in option else "1"
    margin_bottom = str(option['margin_bottom']) if "margin_bottom" in option else "1"

    style = """<style>@page {
        size: """ + (page_size or "a4") + """ """ + (orientation or "landscape") + """;
        left: """ + (margin_left or "1") + (measure_unit or "mm") + """;
        right: """ + (margin_right or "1") + (measure_unit or "mm") + """;
        top: """ + (margin_top or "1") + (measure_unit or "mm") + """;
        bottom: """+(margin_bottom or "1") + (measure_unit or "mm") + """;
    } </style>"""

    if "<head>" in html:
        html.replace("<head>", "<head>"+style)
    elif "<html>" in html:
        html.replace("<html>", "<html>" + style)
    else:
        html = style+html

    # Generate PDF to lambda tmp
    pdf_file = "%s_%s.pdf" % (option['filename_prefix'], time_str)
    result_file = open('/tmp/' + pdf_file, 'w+b')
    pisa_status = pisa.CreatePDF(html, dest=result_file)

    return pisa_status


def put_to_s3(html, option, host, bucket_name):
    response = dict()
    s3 = boto3.resource('s3')

    try:
        pdf_file = "%s_%s.pdf" % (option['filename_prefix'], time_str)
        pdf_folder = option['directory_path'] + "/"
        generate_pdf(html, option)
        s3.meta.client.upload_file('/tmp/' + pdf_file,
                                   bucket_name, pdf_folder+pdf_file)
    except Exception as e:
        api_exception_json = custom_exception(e)
        return api_exception_json

    # Remove file from tmp after move to s3
    if os.path.isfile('/tmp/' + pdf_file):
        os.remove('/tmp/' + pdf_file)

    response['file_url'] = "%s/%s%s" % (host, pdf_folder, pdf_file)
    response['code'] = "00"
    response['message'] = "success"

    return response


def lambda_handler(event, context):
    data = event['body']
    host = event['host']
    bucket_name = event['bucket_name']
    html = data['html']
    option = data['option']

    return put_to_s3(html, option, host, bucket_name)

