from .models import Hunt, User, Puzzle, PuzzleImage, HuntImage, Rule, Announcement
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
        fields = ['id', 'name', 'slug', 'description', 'start_date', 'end_date', 'created_at',
                  'poster_img', 'number_of_skips_for_each_team', 'organizers', 'participants', 'payment_completed']


class PuzzleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Puzzle
        fields = ['id', 'hunt', 'name',
                  'description', 'answer', 'type', 'points']


class PuzzleImageSerializer(serializers.ModelSerializer):
    puzzle = PuzzleSerializer(many=False, required=False)

    class Meta:
        model = PuzzleImage
        fields = ['id', 'puzzle', 'image']


class HuntImageSerializer(serializers.ModelSerializer):
    hunt = HuntSerializer(many=False, required=False)

    class Meta:
        model = HuntImage
        fields = ['id', 'hunt', 'image']


class RuleSerializer(serializers.ModelSerializer):
    hunt = HuntSerializer(many=False, required=False)

    class Meta:
        model = Rule
        fields = ['id', 'hunt', 'rule']


class AnnouncementSerializer(serializers.ModelSerializer):
    hunt = HuntSerializer(many=False, required=False)
    creator = UserDataSerializer(many=False, required=False)

    class Meta:
        model = Announcement
        fields = ['id', 'hunt', 'text', 'creator', 'created_at']
