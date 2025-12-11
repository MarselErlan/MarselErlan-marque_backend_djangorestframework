# Generated migration to fix django_admin_log foreign key

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_address_comment_address_entrance_address_floor'),
        ('admin', '0001_initial'),  # Ensure admin app is migrated
    ]

    operations = [
        # Step 1: Delete orphaned log entries (entries where user_id doesn't exist in users table)
        migrations.RunSQL(
            sql="""
                DELETE FROM django_admin_log 
                WHERE user_id NOT IN (SELECT id FROM users);
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        
        # Step 2: Drop the old foreign key constraint pointing to auth_user
        migrations.RunSQL(
            sql="""
                ALTER TABLE django_admin_log 
                DROP CONSTRAINT IF EXISTS django_admin_log_user_id_c564eba6_fk_auth_user_id;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        
        # Step 3: Create new foreign key constraint pointing to users table
        migrations.RunSQL(
            sql="""
                ALTER TABLE django_admin_log 
                ADD CONSTRAINT django_admin_log_user_id_fk_users_id 
                FOREIGN KEY (user_id) REFERENCES users(id) 
                ON DELETE CASCADE;
            """,
            reverse_sql="""
                ALTER TABLE django_admin_log 
                DROP CONSTRAINT IF EXISTS django_admin_log_user_id_fk_users_id;
            """,
        ),
    ]
