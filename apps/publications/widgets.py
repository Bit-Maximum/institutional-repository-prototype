from django.forms.widgets import ClearableFileInput


class EditorClearableFileInput(ClearableFileInput):
    template_name = "publications/widgets/editor_clearable_file_input.html"


class EditorClearableImageInput(ClearableFileInput):
    template_name = "publications/widgets/editor_clearable_image_input.html"
