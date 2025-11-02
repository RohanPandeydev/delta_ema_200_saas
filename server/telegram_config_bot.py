"""
Telegram Config Bot - Dynamic Trading Bot Configuration Manager
================================================================
Allows authorized users to update bot configuration via Telegram
and automatically restart the Docker container with new .env values.
"""

import os
import re
import json
import subprocess
import shutil
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram_notifier import TelegramNotifier


class ConfigBot:
    """Telegram bot for managing trading bot configuration"""
    
    # Authorized user IDs (comma-separated in env var)
    AUTHORIZED_USERS = os.getenv('AUTHORIZED_TELEGRAM_IDS', '').split(',')
    AUTHORIZED_USERS = [uid.strip() for uid in AUTHORIZED_USERS if uid.strip()]
    
    # Valid config keys and their validation rules
    VALID_CONFIGS = {
        'ORDER_SIZE': {'type': float, 'min': 0.001, 'max': 100},
        'SYMBOL': {'type': str, 'pattern': r'^[A-Z]{3,10}$'},
        'RSI_PERIOD': {'type': int, 'min': 2, 'max': 50},
        'RSI_OVERBOUGHT': {'type': int, 'min': 50, 'max': 100},
        'RSI_OVERSOLD': {'type': int, 'min': 0, 'max': 50},
        'SMA_PERIOD': {'type': int, 'min': 2, 'max': 200},
        'TV_SYMBOL': {'type': str, 'pattern': r'^[A-Z:]{5,20}$'},
        'TIMEFRAME_1M': {'type': int, 'min': 1, 'max': 1440},
        'LOT_SIZE': {'type': float, 'min': 0.001, 'max': 100},
    }
    
    def __init__(self):
        self.env_file = '/app/.env'
        self.env_backup = '/app/.env.backup'
        self.pending_updates = {}
        
        # Initialize trading bot notifier (separate from config bot)
        trading_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        trading_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.trading_notifier = TelegramNotifier(trading_bot_token, trading_chat_id)
    
    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        return str(user_id) in self.AUTHORIZED_USERS
    
    def notify_config_change(self, user_name: str, changes: dict, action: str):
        """Send notification to trading bot channel about config changes"""
        if not self.trading_notifier.enabled:
            return
        
        # Build changes list
        changes_text = ""
        for key, value in changes.items():
            changes_text += f"• {key} = {value}\n"
        
        # Determine action emoji and text
        if action == "restart":
            action_emoji = "🔄"
            action_text = "RESTARTED"
        elif action == "rebuild":
            action_emoji = "🔨"
            action_text = "REBUILT"
        else:
            action_emoji = "💾"
            action_text = "UPDATED"
        
        message = f"""
{action_emoji} <b>CONFIGURATION {action_text}</b>

👤 <b>Changed by:</b> {user_name}

📝 <b>Changes Applied:</b>
{changes_text}

⏰ {self.trading_notifier._get_timestamp()}

ℹ️ <i>Bot will use new configuration on next signal</i>
"""
        
        self.trading_notifier._send_message(message)
    
    def parse_config_message(self, message: str) -> dict:
        """Parse config message into key-value pairs"""
        configs = {}
        errors = []
        
        # Split by lines
        lines = message.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Match KEY=VALUE or KEY="VALUE"
            match = re.match(r'^([A-Z_0-9]+)\s*=\s*(.+)$', line)
            if not match:
                errors.append(f"Invalid format: {line}")
                continue
            
            key, value = match.groups()
            
            # Remove quotes
            value = value.strip().strip('"').strip("'")
            
            if key not in self.VALID_CONFIGS:
                errors.append(f"Unknown config: {key}")
                continue
            
            # Validate
            validation = self.VALID_CONFIGS[key]
            try:
                # Convert type
                if validation['type'] == int:
                    parsed_value = int(value)
                    if 'min' in validation and parsed_value < validation['min']:
                        errors.append(f"{key}: value {parsed_value} < min {validation['min']}")
                        continue
                    if 'max' in validation and parsed_value > validation['max']:
                        errors.append(f"{key}: value {parsed_value} > max {validation['max']}")
                        continue
                
                elif validation['type'] == float:
                    parsed_value = float(value)
                    if 'min' in validation and parsed_value < validation['min']:
                        errors.append(f"{key}: value {parsed_value} < min {validation['min']}")
                        continue
                    if 'max' in validation and parsed_value > validation['max']:
                        errors.append(f"{key}: value {parsed_value} > max {validation['max']}")
                        continue
                
                elif validation['type'] == str:
                    parsed_value = value
                    if 'pattern' in validation:
                        if not re.match(validation['pattern'], parsed_value):
                            errors.append(f"{key}: invalid format '{parsed_value}'")
                            continue
                
                configs[key] = str(parsed_value)
            
            except ValueError as e:
                errors.append(f"{key}: invalid value '{value}' (expected {validation['type'].__name__})")
        
        return {'configs': configs, 'errors': errors}
    
    def read_current_config(self) -> dict:
        """Read current configuration from .env file"""
        config = {}
        
        if not os.path.exists(self.env_file):
            return config
        
        try:
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    match = re.match(r'^([A-Z_0-9]+)\s*=\s*(.+)$', line)
                    if match:
                        key, value = match.groups()
                        value = value.strip().strip('"').strip("'")
                        config[key] = value
        except Exception as e:
            print(f"Error reading config: {e}")
        
        return config
    
    def backup_config(self) -> bool:
        """Backup current .env file"""
        try:
            if os.path.exists(self.env_file):
                shutil.copy2(self.env_file, self.env_backup)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                shutil.copy2(self.env_file, f'{self.env_backup}.{timestamp}')
                return True
        except Exception as e:
            print(f"Backup failed: {e}")
            return False
    
    def update_env_file(self, updates: dict) -> bool:
        """Update .env file with new values"""
        try:
            # Backup first
            if not self.backup_config():
                return False
            
            # Read current config
            current = self.read_current_config()
            
            # Update with new values
            current.update(updates)
            
            # Write back
            with open(self.env_file, 'w') as f:
                f.write("# Trading Bot Configuration\n")
                f.write(f"# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for key, value in sorted(current.items()):
                    f.write(f'{key}="{value}"\n')
            
            return True
        
        except Exception as e:
            print(f"Update failed: {e}")
            return False
    
    def restart_docker(self) -> tuple[bool, str]:
        """Restart Docker container to load new .env values - FIXED VERSION"""
        try:
            container_name = "trading_bot_avi_da_rsi_sma_test_two_way"
            
            print("🔄 Restarting trading bot container...")
            
            # Method 1: Simple restart (preserves container, reloads .env)
            result = subprocess.run(
                ['docker', 'restart', container_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Wait for container to fully start
                time.sleep(5)
                return True, "Container restarted successfully with new configuration"
            
            # Method 2: If restart fails, try stop + start
            print("Restart failed, trying stop/start...")
            
            # Stop container
            stop_result = subprocess.run(
                ['docker', 'stop', container_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if stop_result.returncode != 0:
                return False, f"Failed to stop container: {stop_result.stderr}"
            
            # Wait a moment
            time.sleep(3)
            
            # Start container
            start_result = subprocess.run(
                ['docker', 'start', container_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if start_result.returncode == 0:
                time.sleep(5)
                return True, "Container stopped and started successfully with new configuration"
            else:
                return False, f"Failed to start container: {start_result.stderr}"
        
        except subprocess.TimeoutExpired:
            return False, "Operation timed out"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def rebuild_docker(self) -> tuple[bool, str]:
        """Rebuild Docker image and restart container"""
        try:
            container_name = "trading_bot_avi_da_rsi_sma_test_two_way"
            
            print("🔨 Rebuilding Docker container...")
            
            # Change to app directory
            os.chdir('/app')
            
            # Rebuild and restart using docker-compose
            result = subprocess.run(
                ['docker-compose', 'up', '-d', '--build', 'ema_trading_bot'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return True, "Container rebuilt successfully with new code and configuration"
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                return False, f"Rebuild failed: {error_msg}"
        
        except subprocess.TimeoutExpired:
            return False, "Rebuild operation timed out"
        except Exception as e:
            return False, f"Rebuild error: {str(e)}"

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        
        if not self.is_authorized(user_id):
            await update.message.reply_text(
                "❌ <b>Unauthorized Access</b>\n\n"
                "You are not authorized to use this bot.\n"
                f"Your user ID: <code>{user_id}</code>",
                parse_mode='HTML'
            )
            return
        
        welcome_msg = (
            "🤖 <b>Trading Bot Config Manager</b>\n\n"
            "Welcome! I can help you manage your trading bot configuration.\n\n"
            "<b>Available Commands:</b>\n"
            "/config - Show current configuration\n"
            "/update - Update configuration\n"
            "/restart - Restart bot (no rebuild)\n"
            "/rebuild - Rebuild and restart bot\n"
            "/status - Show bot status\n"
            "/help - Show this help message\n\n"
            "To update config, use:\n"
            "<code>/update\n"
            "ORDER_SIZE=1\n"
            "RSI_PERIOD=14\n"
            "SMA_PERIOD=21\n"
            "TIMEFRAME_1M=60</code>\n\n"
            "✨ <i>Changes will be notified to your trading channel!</i>"
        )
        
        await update.message.reply_text(welcome_msg, parse_mode='HTML')
    
    async def config_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current configuration"""
        user_id = update.effective_user.id
        
        if not self.is_authorized(user_id):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        config = self.read_current_config()
        
        if not config:
            await update.message.reply_text("⚠️ No configuration found")
            return
        
        # Format config
        config_text = "📊 <b>Current Configuration</b>\n\n"
        
        for key in self.VALID_CONFIGS.keys():
            value = config.get(key, 'Not set')
            config_text += f"<code>{key}</code> = <b>{value}</b>\n"
        
        config_text += f"\n<i>Last read: {datetime.now().strftime('%H:%M:%S')}</i>"
        
        await update.message.reply_text(config_text, parse_mode='HTML')
    
    async def update_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /update command"""
        user_id = update.effective_user.id
        
        if not self.is_authorized(user_id):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        # Check if config provided
        if not context.args:
            example = (
                "📝 <b>Update Configuration</b>\n\n"
                "Send your config in the following format:\n\n"
                "<code>/update\n"
                "ORDER_SIZE=1\n"
                "SYMBOL=BTCUSD\n"
                "RSI_PERIOD=14\n"
                "SMA_PERIOD=21\n"
                "TIMEFRAME_1M=60</code>\n\n"
                "Or just paste the config values (without /update):\n\n"
                "<code>ORDER_SIZE=1\n"
                "SYMBOL=BTCUSD\n"
                "TIMEFRAME_1M=60</code>"
            )
            await update.message.reply_text(example, parse_mode='HTML')
            return
        
        # Parse message (skip /update command)
        message = update.message.text.replace('/update', '', 1).strip()
        await self.process_config_update(update, message)
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle plain text messages (config updates)"""
        user_id = update.effective_user.id
        
        if not self.is_authorized(user_id):
            return
        
        message = update.message.text.strip()
        
        # Check if it looks like config
        if '=' in message and any(key in message for key in self.VALID_CONFIGS.keys()):
            await self.process_config_update(update, message)
    
    async def process_config_update(self, update: Update, message: str):
        """Process configuration update"""
        user_id = update.effective_user.id
        
        # Parse config
        result = self.parse_config_message(message)
        configs = result['configs']
        errors = result['errors']
        
        if errors:
            error_text = "❌ <b>Validation Errors:</b>\n\n"
            for error in errors:
                error_text += f"• {error}\n"
            
            await update.message.reply_text(error_text, parse_mode='HTML')
            return
        
        if not configs:
            await update.message.reply_text("⚠️ No valid configuration found")
            return
        
        # Store pending updates
        self.pending_updates[user_id] = configs
        
        # Show preview
        preview = "✅ <b>Configuration Validated</b>\n\n"
        preview += "<b>Changes to be applied:</b>\n\n"
        
        current = self.read_current_config()
        
        for key, new_value in configs.items():
            old_value = current.get(key, 'Not set')
            if old_value != new_value:
                preview += f"<code>{key}</code>\n"
                preview += f"  Old: <b>{old_value}</b>\n"
                preview += f"  New: <b>{new_value}</b> ✨\n\n"
            else:
                preview += f"<code>{key}</code> = <b>{new_value}</b> (unchanged)\n\n"
        
        preview += "\n💡 <b>Choose action:</b>\n"
        preview += "• <b>Apply & Restart</b>: Save + reload container ✅ <i>(Recommended)</i>\n"
        preview += "• <b>Apply Only</b>: Save to .env (manual restart needed)\n"
        preview += "• <b>Apply & Rebuild</b>: Full rebuild (only for code changes)\n"
        
        # Create confirmation buttons
        keyboard = [
            [
                InlineKeyboardButton("🔄 Apply & Restart ✅", callback_data='apply_restart'),
                InlineKeyboardButton("❌ Cancel", callback_data='cancel')
            ],
            [
                # InlineKeyboardButton("💾 Apply Only", callback_data='apply'),
                # InlineKeyboardButton("🔨 Rebuild (Advanced)", callback_data='apply_rebuild')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            preview,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        user_id = query.from_user.id
        user_name = query.from_user.first_name or f"User {user_id}"
        
        if not self.is_authorized(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        
        await query.answer()
        
        action = query.data
        
        if action == 'cancel':
            self.pending_updates.pop(user_id, None)
            await query.edit_message_text("❌ Update cancelled")
            return
        
        # Get pending updates
        updates = self.pending_updates.get(user_id)
        if not updates:
            await query.edit_message_text("⚠️ No pending updates found")
            return
        
        # Apply updates
        if action in ['apply', 'apply_restart', 'apply_rebuild']:
            await query.edit_message_text("⏳ Applying configuration changes...")
            
            success = self.update_env_file(updates)
            
            if not success:
                await query.edit_message_text("❌ Failed to update configuration")
                return
            
            result_msg = "✅ <b>Configuration Updated</b>\n\n"
            for key, value in updates.items():
                result_msg += f"<code>{key}</code> = <b>{value}</b>\n"
            
            # Determine action type for notification
            action_type = "saved"
            
            # Restart or rebuild if requested
            if action == 'apply_restart':
                result_msg += "\n⏳ Restarting container..."
                await query.edit_message_text(result_msg, parse_mode='HTML')
                
                success, message = self.restart_docker()
                if success:
                    result_msg += f"\n✅ {message}"
                    action_type = "restart"
                else:
                    result_msg += f"\n❌ {message}"
            
            elif action == 'apply_rebuild':
                result_msg += "\n⏳ Rebuilding container (this may take a few minutes)..."
                await query.edit_message_text(result_msg, parse_mode='HTML')
                
                success, message = self.rebuild_docker()
                if success:
                    result_msg += f"\n✅ {message}"
                    action_type = "rebuild"
                else:
                    result_msg += f"\n❌ {message}"
            
            # Send notification to trading channel
            self.notify_config_change(user_name, updates, action_type)
            
            result_msg += "\n\n📢 <i>Notification sent to trading channel</i>"
            
            await query.edit_message_text(result_msg, parse_mode='HTML')
            self.pending_updates.pop(user_id, None)
    
    async def restart_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Restart bot without rebuild"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or f"User {user_id}"
        
        if not self.is_authorized(user_id):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        await update.message.reply_text("⏳ Restarting container...")
        
        success, message = self.restart_docker()
        
        if success:
            # Notify trading channel
            self.notify_config_change(user_name, {"Action": "Manual Restart"}, "restart")
            await update.message.reply_text(f"✅ {message}\n\n📢 <i>Notification sent to trading channel</i>", parse_mode='HTML')
        else:
            await update.message.reply_text(f"❌ {message}")
    
    async def rebuild_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Rebuild and restart bot"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or f"User {user_id}"
        
        if not self.is_authorized(user_id):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        await update.message.reply_text("⏳ Rebuilding container...")
        
        success, message = self.rebuild_docker()
        
        if success:
            # Notify trading channel
            self.notify_config_change(user_name, {"Action": "Manual Rebuild"}, "rebuild")
            await update.message.reply_text(f"✅ {message}\n\n📢 <i>Notification sent to trading channel</i>", parse_mode='HTML')
        else:
            await update.message.reply_text(f"❌ {message}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot status"""
        user_id = update.effective_user.id
        
        if not self.is_authorized(user_id):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        try:
            # Check container status
            result = subprocess.run(
                ['docker', 'ps', '-a', '--filter', 'name=trading_bot'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            status = "📊 <b>Bot Status</b>\n\n"
            
            if result.stdout.strip():
                status += f"<pre>{result.stdout}</pre>"
            else:
                status += "⚠️ No trading bot containers found\n"
            
            # Add config bot status
            config_result = subprocess.run(
                ['docker', 'ps', '-a', '--filter', 'name=trading_config_bot'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            status += "\n<b>Config Bot Status:</b>\n"
            if config_result.stdout.strip():
                status += f"<pre>{config_result.stdout}</pre>"
            else:
                status += "⚠️ Config bot not running\n"
            
            # Add notification status
            if self.trading_notifier.enabled:
                status += "\n\n✅ <i>Trading notifications: Enabled</i>"
            else:
                status += "\n\n⚠️ <i>Trading notifications: Disabled</i>"
            
            await update.message.reply_text(status, parse_mode='HTML')
        
        except Exception as e:
            await update.message.reply_text(f"❌ Error checking status: {str(e)}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help"""
        await self.start_command(update, context)
    
    def run(self):
        """Run the bot"""
        token = os.getenv('CONFIG_BOT_TOKEN')
        
        if not token:
            print("❌ CONFIG_BOT_TOKEN not set")
            return
        
        if not self.AUTHORIZED_USERS:
            print("❌ AUTHORIZED_TELEGRAM_IDS not set")
            return
        
        print(f"✅ Starting Config Bot")
        print(f"✅ Authorized users: {', '.join(self.AUTHORIZED_USERS)}")
        
        if self.trading_notifier.enabled:
            print(f"✅ Trading notifications enabled")
        else:
            print(f"⚠️ Trading notifications disabled")
        
        # Create application
        application = Application.builder().token(token).build()
        
        # Add handlers
        application.add_handler(CommandHandler('start', self.start_command))
        application.add_handler(CommandHandler('config', self.config_command))
        application.add_handler(CommandHandler('update', self.update_command))
        application.add_handler(CommandHandler('restart', self.restart_command))
        application.add_handler(CommandHandler('rebuild', self.rebuild_command))
        application.add_handler(CommandHandler('status', self.status_command))
        application.add_handler(CommandHandler('help', self.help_command))
        
        # Button handlers
        application.add_handler(CallbackQueryHandler(
            self.button_callback,
            pattern='^(apply_restart|cancel)$'
        ))
        
        # Message handler for plain text config
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.message_handler
        ))
        
        # Run
        print("🚀 Config Bot started!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    bot = ConfigBot()
    bot.run()