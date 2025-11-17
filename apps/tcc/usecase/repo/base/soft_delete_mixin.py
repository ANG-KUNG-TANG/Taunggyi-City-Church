class SoftDeleteMixin:
    def _soft_delete(self, obj, user):
        if hasattr(obj, "soft_delete"):
            obj.soft_delete(user=user)
        else:
            obj.is_active = False
            obj.save()
