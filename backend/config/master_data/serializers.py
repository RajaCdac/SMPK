from datetime import datetime

from rest_framework import serializers

from .models import FiPmMhBank, FiPmMhBankAbbr, FiPnMhEarndedn
from .services.bank_service import allocate_bank_cd


class DateFromDateTimeField(serializers.DateField):
    """Local MySQL stores Oracle DATE as DATETIME.

    Django DateField then yields datetime objects, and DRF DateField refuses
    to coerce them (timezone loss). Strip to date for read-only audit fields.
    """

    def to_representation(self, value):
        if isinstance(value, datetime):
            value = value.date()
        return super().to_representation(value)


class FiPmMhBankSerializer(serializers.ModelSerializer):
    date_created = DateFromDateTimeField(read_only=True, allow_null=True)
    date_modified = DateFromDateTimeField(read_only=True, allow_null=True)
    bank_type = serializers.CharField(
        required=False, allow_blank=True, max_length=2
    )
    disp_bank_name = serializers.CharField(read_only=True)
    disp_bank_id = serializers.CharField(read_only=True)
    control_bank_desc = serializers.CharField(read_only=True)

    class Meta:
        model = FiPmMhBank
        fields = [
            "bank_cd",
            "bank_type",
            "disp_bank_name",
            "disp_bank_id",
            "bank_desc",
            "bank_id",
            "control_bank_cd",
            "control_bank_desc",
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
            "disp_bank_name",
            "disp_bank_id",
            "control_bank_desc",
            "date_created",
            "created_by",
            "date_modified",
            "modified_by",
        ]
        extra_kwargs = {
            "bank_cd": {"required": False, "allow_blank": True},
        }

    def _bank_type(self, attrs, instance=None):
        raw = (attrs.get("bank_type") or "").strip().upper()
        if raw:
            return raw[:2]
        code = (attrs.get("bank_cd") or getattr(instance, "bank_cd", "") or "").strip()
        return code[:2].upper()

    def _require_abbr(self, bank_type):
        if len(bank_type) != 2:
            raise serializers.ValidationError(
                {
                    "bank_type": "Select the bank from Bank Abbreviation Master first.",
                }
            )
        abbr = FiPmMhBankAbbr.objects.filter(bank_type__iexact=bank_type).first()
        if not abbr:
            raise serializers.ValidationError(
                {
                    "bank_type": (
                        "Sorry !. This Bank is not available in Bank Abbreviation "
                        "Master. Enter the Bank Abbreviation first."
                    )
                }
            )
        return abbr

    def _reject_duplicate_branch_id(self, bank_type, branch_id, instance=None):
        code = (branch_id or "").strip()
        if not code:
            return
        # On update: if the branch_id hasn't changed from the existing record, skip.
        if instance and (instance.bank_id or "").strip().upper() == code.upper():
            return
        qs = FiPmMhBank.objects.filter(
            bank_id__iexact=code,
            bank_cd__istartswith=bank_type,
        )
        if instance and instance.pk:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {
                    "bank_id": (
                        "One entry with this Bank ID and Branch ID has already been done"
                    )
                }
            )

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        bank_type = self._bank_type(attrs, instance)
        if not instance or not instance.pk:
            self._require_abbr(bank_type)
        branch_id = attrs["bank_id"] if "bank_id" in attrs else getattr(
            instance, "bank_id", ""
        )
        self._reject_duplicate_branch_id(bank_type, branch_id, instance=instance)
        control = (
            attrs["control_bank_cd"]
            if "control_bank_cd" in attrs
            else getattr(instance, "control_bank_cd", "")
        )
        control = (control or "").strip()
        if control and bank_type and not control.upper().startswith(bank_type):
            raise serializers.ValidationError(
                {
                    "control_bank_cd": (
                        "Controlling branch must belong to the selected bank."
                    )
                }
            )
        attrs["bank_type"] = bank_type
        return attrs

    def create(self, validated_data):
        bank_type = validated_data.pop("bank_type", "")
        if not (validated_data.get("bank_cd") or "").strip():
            try:
                validated_data["bank_cd"] = allocate_bank_cd(bank_type)
            except ValueError as exc:
                raise serializers.ValidationError({"bank_type": str(exc)}) from exc
        else:
            validated_data["bank_cd"] = validated_data["bank_cd"].strip().upper()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("bank_type", None)
        validated_data.pop("bank_cd", None)
        return super().update(instance, validated_data)

    def _abbr_by_type(self):
        cache = getattr(self, "_abbr_by_type_cache", None)
        if cache is None:
            cache = {
                str(row.bank_type).upper(): row
                for row in FiPmMhBankAbbr.objects.all().order_by("bank_type")
            }
            self._abbr_by_type_cache = cache
        return cache

    def to_representation(self, instance):
        data = super().to_representation(instance)
        prefix = (instance.bank_cd or "")[:2].upper()
        data["bank_type"] = prefix
        abbr = self._abbr_by_type().get(prefix)
        data["disp_bank_name"] = abbr.bank_name if abbr else ""
        data["disp_bank_id"] = abbr.bank_id if abbr else ""
        ctrl = (instance.control_bank_cd or "").strip()
        if ctrl:
            ctrl_row = FiPmMhBank.objects.filter(bank_cd=ctrl).first()
            data["control_bank_desc"] = ctrl_row.bank_desc if ctrl_row else ""
        else:
            data["control_bank_desc"] = ""
        return data


class FiPmMhBankAbbrSerializer(serializers.ModelSerializer):
    date_created = DateFromDateTimeField(read_only=True, allow_null=True)
    date_modified = DateFromDateTimeField(read_only=True, allow_null=True)

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
    date_created = DateFromDateTimeField(read_only=True, allow_null=True)
    date_modified = DateFromDateTimeField(read_only=True, allow_null=True)

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
