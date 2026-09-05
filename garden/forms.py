from django import forms

from .models import Bed, Plant, ScheduleKind, Task


class PlantForm(forms.ModelForm):
    """Progressive-entry plant form: only common_name is required (AC-124).

    Fields are grouped for the template's collapsible sections; the groups
    mirror the PDD Add/Edit Plant screen.
    """

    photo = forms.ImageField(
        required=False,
        label="Photo",
        widget=forms.ClearableFileInput(attrs={
            "class": "photo-input",
            "accept": "image/*,.heic,.heif",
        }),
        error_messages={
            "invalid_image": (
                "That photo format could not be read. In Photos, export it as JPEG or PNG "
                "and try again."
            ),
        },
    )
    bed = forms.ModelChoiceField(
        queryset=Bed.objects.filter(archived_at__isnull=True),
        required=False,
        label="Yard area / bed",
        empty_label="(no bed yet)",
    )
    location_note = forms.CharField(
        required=False, label="Where in the bed?", help_text='e.g. "north edge, by the fence"'
    )

    class Meta:
        model = Plant
        fields = [
            "common_name", "cultivar", "plant_type",
            "botanical_name", "is_edible", "is_ornamental", "foliage",
            "planted_on", "planted_precision", "source",
            "sun", "water_needs", "soil_notes", "mature_height", "mature_width",
            "bloom_window", "harvest_window", "prune_window", "fertilize_window",
            "toxicity_notes", "notes",
        ]
        widgets = {
            "planted_on": forms.DateInput(attrs={"type": "date"}),
            "soil_notes": forms.Textarea(attrs={"rows": 2}),
            "toxicity_notes": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, garden=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.garden = garden
        if garden is not None:
            self.fields["bed"].queryset = Bed.objects.filter(
                garden=garden, archived_at__isnull=True
            )

    GROUPS = {
        "basics": ["common_name", "cultivar", "photo", "plant_type", "bed", "location_note"],
        "details": ["botanical_name", "is_edible", "is_ornamental", "foliage",
                    "planted_on", "planted_precision", "source"],
        "conditions": ["sun", "water_needs", "soil_notes", "mature_height", "mature_width"],
        "seasons": ["bloom_window", "harvest_window", "prune_window", "fertilize_window"],
        "notes_fields": ["toxicity_notes", "notes"],
    }

    def __getattr__(self, name):
        # Expose field groups to templates: form.basics, form.details, ...
        groups = self.__dict__.get("GROUPS") or type(self).GROUPS
        if name in groups:
            return [self[f] for f in groups[name]]
        raise AttributeError(name)


class TaskForm(forms.ModelForm):
    """Task creation/edit. The template shows only the timing fields relevant
    to the chosen schedule kind; clean() enforces the same rule server-side
    (mirroring the DB check constraint, but with friendly messages)."""

    class Meta:
        model = Task
        fields = [
            "title", "notes", "category", "priority",
            "plants", "beds", "tag",
            "schedule_kind", "due_on", "window",
            "interval_count", "interval_unit", "interval_anchor",
        ]
        widgets = {
            "due_on": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
            "plants": forms.SelectMultiple(attrs={"size": 5}),
            "beds": forms.SelectMultiple(attrs={"size": 4}),
        }

    def __init__(self, *args, garden=None, **kwargs):
        super().__init__(*args, **kwargs)
        plants = Plant.objects.filter(status="active")
        beds = Bed.objects.filter(archived_at__isnull=True)
        if garden is not None:
            plants = plants.filter(garden=garden)
            beds = beds.filter(garden=garden)
        self.fields["plants"].queryset = plants
        self.fields["beds"].queryset = beds
        self.fields["plants"].required = False
        self.fields["beds"].required = False

    def clean(self):
        data = super().clean()
        kind = data.get("schedule_kind")
        if kind in (ScheduleKind.EXACT_ONCE, ScheduleKind.EXACT_YEARLY) and not data.get("due_on"):
            self.add_error("due_on", "Pick the date this is due.")
        window_kinds = (ScheduleKind.WINDOW_ONCE, ScheduleKind.WINDOW_YEARLY)
        if kind in window_kinds and not data.get("window"):
            self.add_error("window", "Pick the seasonal window.")
        if kind == ScheduleKind.INTERVAL:
            if not data.get("interval_count"):
                self.add_error("interval_count", "How often? e.g. every 6 weeks.")
            if not data.get("interval_unit"):
                self.add_error("interval_unit", "Days, weeks, or months?")
        return data


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    """Multiple-photo upload (Django's documented multi-file pattern)."""

    widget = MultiFileInput

    def clean(self, data, initial=None):
        single = super().clean
        if isinstance(data, list | tuple):
            return [single(d, initial) for d in data]
        return [single(data, initial)] if data else []


class ActivityForm(forms.ModelForm):
    photos_upload = MultiFileField(required=False, label="Photos")

    class Meta:
        from .models import Activity

        model = Activity
        fields = ["activity_type", "performed_on", "note"]
        widgets = {
            "performed_on": forms.DateInput(attrs={"type": "date"}),
            "note": forms.Textarea(attrs={"rows": 3}),
        }


class HarvestForm(forms.ModelForm):
    photos_upload = MultiFileField(required=False, label="Photos")

    class Meta:
        from .models import HarvestEvent

        model = HarvestEvent
        fields = ["harvested_on", "quantity", "unit", "count", "quality", "intended_use", "notes"]
        widgets = {
            "harvested_on": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class JournalForm(forms.ModelForm):
    photos_upload = MultiFileField(required=False, label="Photos")

    class Meta:
        from .models import JournalEntry

        model = JournalEntry
        fields = ["text", "plants", "beds", "tags"]
        widgets = {
            "text": forms.Textarea(
                attrs={"rows": 5, "placeholder": "What's happening in the garden?"}
            ),
            "plants": forms.SelectMultiple(attrs={"size": 5}),
            "beds": forms.SelectMultiple(attrs={"size": 4}),
            "tags": forms.SelectMultiple(attrs={"size": 4}),
        }

    def __init__(self, *args, garden=None, **kwargs):
        super().__init__(*args, **kwargs)
        plants = Plant.objects.filter(status="active")
        beds = Bed.objects.filter(archived_at__isnull=True)
        if garden is not None:
            plants = plants.filter(garden=garden)
            beds = beds.filter(garden=garden)
        self.fields["plants"].queryset = plants
        self.fields["beds"].queryset = beds
        for name in ("plants", "beds", "tags"):
            self.fields[name].required = False


class PhotoForm(forms.ModelForm):
    class Meta:
        from .models import Photo

        model = Photo
        fields = ["file", "taken_on", "caption", "categories"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={
                "class": "photo-input",
                "accept": "image/*,.heic,.heif",
            }),
            "taken_on": forms.DateInput(attrs={"type": "date"}),
            "categories": forms.CheckboxSelectMultiple,
        }


class BedForm(forms.ModelForm):
    class Meta:
        from .models import Bed

        model = Bed
        fields = ["name", "short_code", "bed_type", "sun_notes", "soil_notes",
                  "irrigation_notes", "notes"]
        widgets = {
            "sun_notes": forms.Textarea(attrs={"rows": 2}),
            "soil_notes": forms.Textarea(attrs={"rows": 2}),
            "irrigation_notes": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, garden=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.garden = garden

    def clean_name(self):
        from .models import Bed

        name = self.cleaned_data["name"].strip()
        clash = Bed.objects.filter(archived_at__isnull=True, name__iexact=name)
        if self.garden is not None:
            clash = clash.filter(garden=self.garden)
        if self.instance.pk:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            # PDD 4.3: prompt for a distinguishing name, never silent ambiguity
            raise forms.ValidationError(
                "There's already a bed with this name - pick something distinguishing."
            )
        return name


class ProblemCaseForm(forms.ModelForm):
    """Log a problem: pick an existing type or name a new one in one step."""

    from .models import ProblemKind

    kind = forms.ChoiceField(choices=ProblemKind.choices, label="What kind of problem?")
    type_name = forms.CharField(
        label="What is it?",
        help_text='e.g. "Bindweed", "Aphids", "Powdery mildew" - reuses the record if it exists',
    )
    photos_upload = MultiFileField(required=False, label="Photos")

    class Meta:
        from .models import ProblemCase

        model = ProblemCase
        fields = [
            "plants", "bed", "location_note", "first_observed",
            "severity", "confidence", "symptoms", "notes", "follow_up_on",
        ]
        widgets = {
            "first_observed": forms.DateInput(attrs={"type": "date"}),
            "follow_up_on": forms.DateInput(attrs={"type": "date"}),
            "symptoms": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 2}),
            "plants": forms.SelectMultiple(attrs={"size": 5}),
        }

    def __init__(self, *args, garden=None, **kwargs):
        super().__init__(*args, **kwargs)
        plants = Plant.objects.filter(status="active")
        beds = Bed.objects.filter(archived_at__isnull=True)
        if garden is not None:
            plants = plants.filter(garden=garden)
            beds = beds.filter(garden=garden)
        self.fields["plants"].queryset = plants
        self.fields["plants"].required = False
        self.fields["bed"].queryset = beds
        self.fields["bed"].required = False


class TreatmentForm(forms.ModelForm):
    photos_upload = MultiFileField(required=False, label="Photos")

    class Meta:
        from .models import Treatment

        model = Treatment
        fields = ["treated_on", "method", "product", "effectiveness", "notes"]
        widgets = {
            "treated_on": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }
