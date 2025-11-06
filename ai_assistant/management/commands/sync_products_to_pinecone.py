"""
Management command to bulk-sync all products to Pinecone
Usage: python manage.py sync_products_to_pinecone
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from products.models import Product
from ai_assistant.pinecone_utils import bulk_sync_products_to_pinecone


class Command(BaseCommand):
    help = 'Sync all active products to Pinecone vector database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--market',
            type=str,
            help='Sync only specific market (KG/US/ALL)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of products per batch (default: 100)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even inactive products',
        )

    def handle(self, *args, **options):
        market = options.get('market')
        batch_size = options.get('batch_size', 100)
        force = options.get('force', False)
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🚀 PINECONE PRODUCT SYNC'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # Build queryset
        queryset = Product.objects.all()
        
        if not force:
            queryset = queryset.filter(is_active=True)
        
        if market:
            queryset = queryset.filter(Q(market=market) | Q(market='ALL'))
            self.stdout.write(f"🌍 Market filter: {market}")
        
        total = queryset.count()
        self.stdout.write(f"📦 Total products to sync: {total}")
        self.stdout.write(f"📊 Batch size: {batch_size}")
        self.stdout.write('')
        
        if total == 0:
            self.stdout.write(self.style.WARNING('⚠️ No products found to sync'))
            return
        
        # Confirm
        self.stdout.write(self.style.WARNING('⚠️ This will sync all products to Pinecone'))
        confirm = input('Continue? (yes/no): ')
        
        if confirm.lower() not in ['yes', 'y']:
            self.stdout.write(self.style.ERROR('❌ Sync cancelled'))
            return
        
        # Perform sync
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('⏳ Syncing products...'))
        
        try:
            synced, failed = bulk_sync_products_to_pinecone(queryset, batch_size=batch_size)
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.SUCCESS('✅ SYNC COMPLETE'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(f"✅ Successfully synced: {synced}/{total}")
            
            if failed > 0:
                self.stdout.write(self.style.WARNING(f"⚠️ Failed: {failed}/{total}"))
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('🎉 Products are now searchable via AI!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error during sync: {str(e)}'))
            raise

