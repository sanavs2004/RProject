import json
import os

class RoleConfigManager:
    """
    Manages role-specific configurations for scoring weights
    Loads ALL configuration from external JSON files - NO HARDCODING
    """
    
    def __init__(self, config_file):
        """
        Initialize with path to config file
        
        Args:
            config_file: Path to JSON configuration file
        """
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """
        Load configuration from JSON file
        Returns empty dict if file doesn't exist (will be created on first save)
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"⚠️ Error parsing {self.config_file}, creating new config")
                return {}
            except Exception as e:
                print(f"⚠️ Error loading config: {e}")
                return {}
        else:
            print(f"📁 Config file {self.config_file} not found. Will create on first save.")
            return {}
    
    def _save_config(self, config):
        """Save configuration to JSON file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"✅ Config saved to {self.config_file}")
            return True
        except Exception as e:
            print(f"⚠️ Error saving config: {e}")
            return False
    
    def get_role_config(self, role, default=None):
        """
        Get configuration for a specific role
        
        Args:
            role: Role name (e.g., 'software_engineer')
            default: Default config to return if role not found
        
        Returns:
            dict: Role configuration or default
        """
        if default is None:
            default = self.get_default_config()
        
        return self.config.get(role, default)
    
    def get_default_config(self):
        """
        Get default configuration
        Returns empty dict if no default configured
        """
        return self.config.get('default', {})
    
    def update_role_config(self, role, config):
        """
        Update configuration for a specific role
        
        Args:
            role: Role name
            config: Configuration dictionary
        """
        self.config[role] = config
        self._save_config(self.config)
        return True
    
    def delete_role_config(self, role):
        """Delete configuration for a role"""
        if role in self.config:
            del self.config[role]
            self._save_config(self.config)
            return True
        return False
    
    def list_roles(self):
        """List all configured roles"""
        return list(self.config.keys())
    
    def create_default_if_missing(self, default_config):
        """
        Create default configuration if file doesn't exist
        
        Args:
            default_config: Default configuration to save
        """
        if not self.config:
            self.config = default_config
            self._save_config(self.config)
            return True
        return False
    
    def validate_config(self, config):
        """
        Validate configuration structure
        
        Returns:
            tuple: (is_valid, errors)
        """
        errors = []
        
        if not isinstance(config, dict):
            errors.append("Config must be a dictionary")
            return False, errors
        
        for role, settings in config.items():
            if not isinstance(settings, dict):
                errors.append(f"Role '{role}' settings must be a dictionary")
                continue
            
            # Check for weights
            if 'weights' in settings:
                weights = settings['weights']
                if not isinstance(weights, dict):
                    errors.append(f"Role '{role}' weights must be a dictionary")
                else:
                    total = sum(weights.values())
                    if abs(total - 1.0) > 0.01:  # Allow small floating point errors
                        errors.append(f"Role '{role}' weights sum to {total}, should be 1.0")
            
            # Check for thresholds
            if 'thresholds' in settings:
                thresholds = settings['thresholds']
                if not isinstance(thresholds, dict):
                    errors.append(f"Role '{role}' thresholds must be a dictionary")
        
        return len(errors) == 0, errors