import uuid
from sqlalchemy import Select, func, literal, select, union_all
from mirix.orm.cloud_file_mapping import CloudFileMapping
from mirix.schemas.cloud_file_mapping import CloudFileMapping as PydanticCloudFileMapping
from mirix.schemas.user import User as PydanticUser

class CloudFileMappingManager:
    """
    A class to manage the mapping of cloud files to local files.
    """

    def __init__(self):
        from mirix.server.server import db_context
        self.session_maker = db_context

    def add_mapping(self, cloud_file_id, local_file_id, timestamp, actor: PydanticUser, force_add=False):
        """
        Add a mapping from a cloud file to a local file.
        """

        # check if cloud_file_id or local_file_id are already in the database
        with self.session_maker() as session:

            # check if cloud_file_id is already in the database for this user
            try:
                existing_mapping = CloudFileMapping.read(session, cloud_file_id=cloud_file_id, actor=actor)
            except Exception:
                existing_mapping = None
            if existing_mapping:
                if force_add:
                    # delete the existing mapping
                    existing_mapping.hard_delete(session)
                else:
                    raise ValueError(f"Mapping already exists for cloud file {cloud_file_id} and local file {local_file_id}")

            try:
                existing_mapping = CloudFileMapping.read(session, local_file_id=local_file_id, actor=actor)
            except Exception:
                existing_mapping = None

            if existing_mapping:
                if force_add:
                    # delete the existing mapping
                    existing_mapping.hard_delete(session)
                else:
                    raise ValueError(f"Mapping already exists for local file {local_file_id} and cloud file {cloud_file_id}")

        pydantic_mapping = PydanticCloudFileMapping(
            cloud_file_id=cloud_file_id,
            local_file_id=local_file_id,
            status='uploaded',
            timestamp=timestamp
        )
        pydantic_mapping_dict = pydantic_mapping.model_dump()
        
        # Validate required fields
        required_fields = ["cloud_file_id", "local_file_id"]
        for field in required_fields:
            if field not in pydantic_mapping_dict or pydantic_mapping_dict[field] is None:
                raise ValueError(f"Required field '{field}' is missing or None in mapping data")
        
        pydantic_mapping_dict.setdefault("id", str(uuid.uuid4()))
        
        # Set organization_id to default organization since this is required by OrganizationMixin
        from mirix.services.organization_manager import OrganizationManager
        pydantic_mapping_dict["organization_id"] = OrganizationManager.DEFAULT_ORG_ID
        
        # Set user_id from actor for multi-user support
        pydantic_mapping_dict["user_id"] = actor.id
        
        with self.session_maker() as session:
            mapping = CloudFileMapping(**pydantic_mapping_dict)
            mapping.create(session)
            return mapping.to_pydantic()

    def get_local_file(self, cloud_file_id, actor: PydanticUser):
        """
        Get the local file associated with a cloud file.
        """
        with self.session_maker() as session:
            mapping = CloudFileMapping.read(session, cloud_file_id=cloud_file_id, actor=actor)
            if mapping:
                return mapping.local_file_id
            else:
                return None
    
    def get_cloud_file(self, local_file_id, actor: PydanticUser):
        """
        Get the cloud file associated with a local file.
        """
        with self.session_maker() as session:
            mapping = CloudFileMapping.read(session, local_file_id=local_file_id, actor=actor)
            if mapping:
                return mapping.cloud_file_id
            else:
                return None
        
    def delete_mapping(self, actor: PydanticUser, cloud_file_id=None, local_file_id=None):
        """
        Delete a mapping between a cloud file and a local file.
        """
        with self.session_maker() as session:

            if cloud_file_id is not None:
                try:
                    mapping = CloudFileMapping.read(session, cloud_file_id=cloud_file_id, actor=actor)
                    mapping.hard_delete(session)
                except Exception:
                    pass
            
            if local_file_id is not None:
                try:
                    mapping = CloudFileMapping.read(session, local_file_id=local_file_id, actor=actor)
                    mapping.hard_delete(session)
                except Exception:
                    pass

    def check_if_existing(self, actor: PydanticUser, cloud_file_id=None, local_file_id=None):
        """
        Check if the file_ids are already in the database
        """
        with self.session_maker() as session:
            if cloud_file_id is not None:
                try:
                    mapping = CloudFileMapping.read(session, cloud_file_id=cloud_file_id, actor=actor)
                    return True
                except:
                    pass
            elif local_file_id is not None:
                try:
                    mapping = CloudFileMapping.read(session, local_file_id=local_file_id, actor=actor)
                    return True
                except:
                    pass
        return False
    
    def set_processed(self, actor: PydanticUser, cloud_file_id=None, local_file_id=None):
        """
        set the "status" as processed
        """
        with self.session_maker() as session:
            mapping = None
            if cloud_file_id is not None:
                try:
                    mapping = CloudFileMapping.read(session, cloud_file_id=cloud_file_id, actor=actor)
                except:
                    pass
            elif local_file_id is not None:
                try:
                    mapping = CloudFileMapping.read(session, local_file_id=local_file_id, actor=actor)
                except:
                    pass
            if mapping is None:
                raise ValueError("File Not Found")
            mapping.status = 'processed'
            mapping.update(session)
            return mapping.to_pydantic()

    def list_files_with_status(self, status, actor: PydanticUser):

        with self.session_maker() as session:
            # Get all files with the specified status for this user and sort by timestamp in ascending order
            stmt = select(CloudFileMapping).where(
                CloudFileMapping.status == status,
                CloudFileMapping.user_id == actor.id
            ).order_by(CloudFileMapping.timestamp.asc())
            results = session.execute(stmt)
            results = results.scalars().all()

            # Convert to Pydantic models
            pydantic_results = [x.to_pydantic() for x in results]
            return pydantic_results

    def list_all_cloud_file_ids(self, actor: PydanticUser):
        """
        List all cloud file IDs for this user.
        """
        with self.session_maker() as session:
            results = session.execute(select(CloudFileMapping).where(
                CloudFileMapping.user_id == actor.id
            ))
            results = results.scalars().all()
            return [x.to_pydantic().cloud_file_id for x in results]
        
    def list_all_local_file_ids(self, actor: PydanticUser):
        """
        List all local file IDs for this user.
        """
        with self.session_maker() as session:
            results = session.execute(select(CloudFileMapping).where(
                CloudFileMapping.user_id == actor.id
            ))
            results = results.scalars().all()
            return [x.to_pydantic().local_file_id for x in results]