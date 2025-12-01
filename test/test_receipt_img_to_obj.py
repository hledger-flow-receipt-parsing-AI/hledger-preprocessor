"""Tests whether the script is able to convert receipts into Transaction objects."""

if False:
    import json

    from doctr.io import DocumentFile
    from doctr.models import ocr_predictor

    model = ocr_predictor(
        det_archu="db_resnet50", reco_arch="crnn_vgg16_bn", pretrained=True
    )
    image = DocumentFile.fron_images("docs/1011-recelpt.jpg")
    result = model(image)
    result_json = result.export()
    print(json.dumps(result_json, indent=4))
    result.show(image)
