from django.db import models
from django.utils import timezone


class ReviewDataset(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    version = models.PositiveSmallIntegerField(default=1)
    anchor_date = models.DateField()
    created_at = models.DateTimeField(default=timezone.now)
    accounts = models.JSONField(default=dict)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="one_review_dataset")]
