from django import forms

from .models import Bed, Plant


class PlantForm(forms.ModelForm):
    """Progressive-entry plant form: only common_name is required (AC-124).

    Fields are grouped for the template's collapsible sections; the groups
    mirror the PDD Add/Edit Plant screen.
    """

    photo = forms.ImageField(required=False, label="Photo")
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
