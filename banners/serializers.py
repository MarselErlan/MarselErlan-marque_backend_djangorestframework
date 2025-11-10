"""
Serializers for banner endpoints.
"""

from typing import Optional

from rest_framework import serializers

from .models import Banner


class BannerSerializer(serializers.ModelSerializer):
    """
    Serialize a banner in the format expected by the frontend.
    Ensures image_url is absolute when possible.
    """

    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = (
            "id",
            "title",
            "subtitle",
            "image_url",
            "banner_type",
            "market",
            "button_text",
            "link_url",
            "sort_order",
        )

    def get_image_url(self, obj: Banner) -> Optional[str]:
        if obj.image:
            url = obj.image.url
        else:
            url = obj.image_url

        if not url:
            return None

        # If URL already absolute, return as-is
        if url.startswith("http://") or url.startswith("https://"):
            return url

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url

