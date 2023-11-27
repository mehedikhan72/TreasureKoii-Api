from .models import Hunt, User
from rest_framework import serializers

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name',
                  'email', 'phone', 'password']

        def create(self, validated_data):
            password = validated_data.pop('password')
            user = User(**validated_data)
            user.set_password(password)
            user.save()

            return user
        
class UserDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone']
        
class HuntSerializer(serializers.ModelSerializer):
    organizers = UserDataSerializer(many=True, required=False)
    class Meta:
        model = Hunt
        fields = ['id', 'name', 'slug', 'description', 'start_date', 'end_date', 'created_at', 'poster_img', 'number_of_skips_for_each_team', 'organizers']