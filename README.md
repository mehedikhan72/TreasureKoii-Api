### 1. Token-based Authentication:

#### `POST /token/`
- **View:** `MyTokenObtainPairView`
- **Functionality:** Obtain a pair of access and refresh tokens by providing valid user credentials (email and password).
- **Custom Claims:** Includes custom claims in the access token (email, first_name, last_name, phone).

#### `POST /token/refresh/`
- **View:** `TokenRefreshView`
- **Functionality:** Refresh the access token by providing a valid refresh token.

#### `POST /register/`
- **View:** `register`
- **Functionality:** Register a new user.
- **Fields Required:** `first_name`, `last_name`, `email`, `password`, `phone`.
- **Username Generation:** Automatically generates a unique username based on first and last names.
- **Password Length Check:** Ensures the password is at least 8 characters long.
- **Response:** Returns a success message if the user is created successfully. Returns bad request if there is an error

### 2. Hunt Operations:

#### `GET /hunts/`
- **View:** `HuntListCreateView`
- **Functionality:** Get a list of hunts.
- **Authentication:** Requires a valid access token (IsAuthenticated).
- **Create Hunt:** Allows authenticated users to create a new hunt.

#### `GET /hunt/<slug>/`
- **View:** `HuntDetailView`
- **Functionality:** Retrieve details of a specific hunt by providing its slug.
- **Permission:** Allows any user to view hunt details (AllowAny).

#### `PUT /hunt/<slug>/`
- **View:** `HuntDetailView`
- **Functionality:** Update details of a specific hunt by providing its slug.
- **Permission:** Allows any user to update hunt details (AllowAny).

#### `DELETE /hunt/<slug>/`
- **View:** `HuntDetailView`
- **Functionality:** Delete a specific hunt by providing its slug.
- **Permission:** Allows any user to delete a hunt (AllowAny).

### 3. Serializers:

- `MyTokenObtainPairSerializer`: Extends `TokenObtainPairSerializer` and adds custom claims to the access token.
- `UserRegisterSerializer`: Validates and processes user registration data.
- `HuntSerializer`: Serializes `Hunt` model data.
- `UserDataSerializer`: Serializes user data for hunts.

### 4. Permissions:

- `IsAuthenticated`: Requires users to be authenticated (access token).
- `AllowAny`: Allows any user, authenticated or not.

### 5. Additional Notes:

- The `perform_create` method in `HuntListCreateView` ensures that the current user is added as an organizer when creating a new hunt.
- The `lookup_field` for `HuntDetailView` is set to `'slug'`.

