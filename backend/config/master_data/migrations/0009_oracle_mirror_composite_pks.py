from django.db import migrations, models


def _composite_pk(*field_names):
    return models.CompositePrimaryKey(
        *field_names,
        blank=True,
        editable=False,
        primary_key=True,
        serialize=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("master_data", "0008_fin_ctrl_detail_composite_pk"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="fipnmhearndedn",
                    name="earndedn_cd",
                    field=models.CharField(
                        db_column="EARNDEDN_CD",
                        max_length=3,
                        verbose_name="Earn/dedn code",
                    ),
                ),
                migrations.AddField(
                    model_name="fipnmhearndedn",
                    name="pk",
                    field=_composite_pk("earndedn_cd", "earndedn_type"),
                ),
                migrations.RemoveConstraint(
                    model_name="fipnmhadarate",
                    name="uniq_ada_rate_key",
                ),
                migrations.RemoveField(model_name="fipnmhadarate", name="id"),
                migrations.AddField(
                    model_name="fipnmhadarate",
                    name="pk",
                    field=_composite_pk("wef_dt", "emp_type", "base_cpi_no"),
                ),
                migrations.RemoveConstraint(
                    model_name="fipnmdmaxadmgratuity",
                    name="uniq_maxadm_gratuity_key",
                ),
                migrations.RemoveField(model_name="fipnmdmaxadmgratuity", name="id"),
                migrations.AddField(
                    model_name="fipnmdmaxadmgratuity",
                    name="pk",
                    field=_composite_pk("wef_dt", "gratuity_type", "ret_dt_from"),
                ),
                migrations.RemoveConstraint(
                    model_name="fipnmhdeathgratchart",
                    name="uniq_mh_death_gratchart_key",
                ),
                migrations.RemoveField(model_name="fipnmhdeathgratchart", name="id"),
                migrations.AddField(
                    model_name="fipnmhdeathgratchart",
                    name="pk",
                    field=_composite_pk("wef_dt", "gratuity_type"),
                ),
                migrations.RemoveConstraint(
                    model_name="fipnmddeathgratchart",
                    name="uniq_md_death_gratchart_key",
                ),
                migrations.RemoveField(model_name="fipnmddeathgratchart", name="id"),
                migrations.AddField(
                    model_name="fipnmddeathgratchart",
                    name="pk",
                    field=_composite_pk("tqs_start_yrs", "wef_dt", "gratuity_type"),
                ),
                migrations.RemoveConstraint(
                    model_name="fipnmhservicegratchart",
                    name="uniq_service_gratchart_key",
                ),
                migrations.RemoveField(model_name="fipnmhservicegratchart", name="id"),
                migrations.AddField(
                    model_name="fipnmhservicegratchart",
                    name="pk",
                    field=_composite_pk("wef_dt", "interval_srl"),
                ),
                migrations.RemoveConstraint(
                    model_name="fipnmhbasecpi",
                    name="uniq_base_cpi_key",
                ),
                migrations.RemoveField(model_name="fipnmhbasecpi", name="id"),
                migrations.AddField(
                    model_name="fipnmhbasecpi",
                    name="pk",
                    field=_composite_pk("emp_type", "wef_dt"),
                ),
                migrations.RemoveConstraint(
                    model_name="fipnmdjrnltype",
                    name="uniq_pn_md_jrnltype_key",
                ),
                migrations.RemoveField(model_name="fipnmdjrnltype", name="id"),
                migrations.AddField(
                    model_name="fipnmdjrnltype",
                    name="pk",
                    field=_composite_pk(
                        "jrnal_srl_no",
                        "zonal_cd",
                        "dr_cr_flg",
                        "aloc_cd1",
                        "aloc_cd2",
                        "aloc_cd3",
                    ),
                ),
            ],
        ),
    ]
