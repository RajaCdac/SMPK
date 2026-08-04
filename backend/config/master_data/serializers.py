from rest_framework import serializers

from .models import FiPmMhBank, FiPmMhBankAbbr, FiPnMhEarndedn


class FiPmMhBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiPmMhBank
        fields = [
            "bank_cd",
            "bank_desc",
            "bank_id",
            "control_bank_cd",
            "addr1",
            "addr2",
            "ps",
            "city",
            "dist",
            "state",
            "pin",
            "country",
            "contact1",
            "contact2",
            "fax_no",
            "email_id",
            "rbi_cd",
            "old_bank_cd",
            "date_created",
            "created_by",
            "date_modified",
            "modified_by",
        ]
        read_only_fields = [
            "date_created",
            "created_by",
            "date_modified",
            "modified_by",
        ]


class FiPmMhBankAbbrSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiPmMhBankAbbr
        fields = [
            "bank_type",
            "bank_name",
            "bank_short_name",
            "bank_id",
            "date_created",
            "created_by",
            "date_modified",
            "modified_by",
        ]
        read_only_fields = [
            "date_created",
            "created_by",
            "date_modified",
            "modified_by",
        ]


class FiPnMhEarndednSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiPnMhEarndedn
        fields = [
            "earndedn_cd",
            "earndedn_type",
            "earndedn_desc",
            "date_created",
            "created_by",
            "date_modified",
            "modified_by",
        ]
        read_only_fields = [
            "date_created",
            "created_by",
            "date_modified",
            "modified_by",
        ]
