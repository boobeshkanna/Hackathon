"""
Unit tests for ONDC Schema Mapper

Tests the transformation of ExtractedAttributes to Beckn protocol format.
"""
import pytest
from backend.models.catalog import ExtractedAttributes, CSI, ONDCCatalogItem
from backend.services.ondc_gateway.schema_mapper import (
    map_to_beckn_item,
    build_long_description,
    map_category_to_ondc,
    generate_item_id,
    _truncate_name,
    _truncate_short_desc,
    _build_tags
)


class TestMapToBecknItem:
    """Test map_to_beckn_item function"""
    
    def test_basic_mapping(self):
        """Test basic attribute mapping to Beckn item"""
        extracted = ExtractedAttributes(
            category="handloom saree",
            subcategory="Banarasi Silk",
            material=["silk", "zari"],
            colors=["red", "gold"],
            price={"value": 5000, "currency": "INR"},
            short_description="Beautiful handwoven Banarasi silk saree",
            long_description="This exquisite Banarasi silk saree features intricate zari work and traditional motifs.",
            craft_technique="Handwoven on pit loom",
            region_of_origin="Varanasi, Uttar Pradesh"
        )
        
        result = map_to_beckn_item(extracted, image_urls=["https://example.com/image1.jpg"])
        
        assert isinstance(result, ONDCCatalogItem)
        assert result.id.startswith("item_")
        assert result.descriptor.name == "Beautiful handwoven Banarasi silk saree"
        assert result.descriptor.short_desc == "Beautiful handwoven Banarasi silk saree"
        assert "Banarasi silk saree" in result.descriptor.long_desc
        assert result.price.value == "5000"
        assert result.price.currency == "INR"
        assert result.category_id == "Fashion:Ethnic Wear:Sarees"
        assert result.descriptor.images == ["https://example.com/image1.jpg"]
    
    def test_mapping_with_csis(self):
        """Test mapping preserves CSI terms"""
        csi = CSI(
            vernacular_term="बनारसी",
            transliteration="Banarasi",
            english_context="Traditional silk weaving style from Varanasi",
            cultural_significance="Represents centuries-old weaving tradition"
        )
        
        extracted = ExtractedAttributes(
            category="saree",
            material=["silk"],
            colors=["red"],
            price={"value": 3000, "currency": "INR"},
            short_description="Banarasi saree",
            long_description="Traditional Banarasi silk saree",
            csis=[csi]
        )
        
        result = map_to_beckn_item(extracted)
        
        assert "Cultural Significance" in result.descriptor.long_desc
        assert "बनारसी" in result.descriptor.long_desc
        assert "Banarasi" in result.descriptor.long_desc
        assert result.tags.get("csi_1_term") == "बनारसी"
        assert result.tags.get("csi_1_transliteration") == "Banarasi"
    
    def test_mapping_without_price(self):
        """Test mapping handles missing price gracefully"""
        extracted = ExtractedAttributes(
            category="pottery",
            material=["clay"],
            colors=["brown"],
            short_description="Handmade clay pot",
            long_description="Traditional handmade clay pot"
        )
        
        result = map_to_beckn_item(extracted)
        
        assert result.price.value == "0"
        assert result.price.currency == "INR"
    
    def test_long_name_truncation(self):
        """Test that long names are truncated properly"""
        long_name = "A" * 150
        extracted = ExtractedAttributes(
            category="handicraft",
            material=["wood"],
            colors=["brown"],
            short_description=long_name,
            long_description="Description"
        )
        
        result = map_to_beckn_item(extracted)
        
        assert len(result.descriptor.name) <= 100
        assert result.descriptor.name.endswith("...")


class TestBuildLongDescription:
    """Test build_long_description function"""
    
    def test_basic_description(self):
        """Test basic description building"""
        extracted = ExtractedAttributes(
            category="pottery",
            material=["clay"],
            colors=["brown"],
            short_description="Clay pot",
            long_description="A beautiful handmade clay pot"
        )
        
        result = build_long_description(extracted)
        
        assert "A beautiful handmade clay pot" in result
    
    def test_description_with_csi(self):
        """Test description includes CSI information"""
        csi = CSI(
            vernacular_term="मिट्टी का बर्तन",
            transliteration="Mitti ka bartan",
            english_context="Traditional clay vessel",
            cultural_significance="Used in traditional cooking"
        )
        
        extracted = ExtractedAttributes(
            category="pottery",
            material=["clay"],
            colors=["brown"],
            short_description="Clay pot",
            long_description="Traditional clay pot",
            csis=[csi]
        )
        
        result = build_long_description(extracted)
        
        assert "Cultural Significance" in result
        assert "मिट्टी का बर्तन" in result
        assert "Mitti ka bartan" in result
        assert "Traditional clay vessel" in result
    
    def test_description_with_craft_technique(self):
        """Test description includes craft technique"""
        extracted = ExtractedAttributes(
            category="pottery",
            material=["clay"],
            colors=["brown"],
            short_description="Clay pot",
            long_description="Handmade pot",
            craft_technique="Hand-thrown on potter's wheel"
        )
        
        result = build_long_description(extracted)
        
        assert "Craft Technique" in result
        assert "Hand-thrown on potter's wheel" in result
    
    def test_description_with_region(self):
        """Test description includes region of origin"""
        extracted = ExtractedAttributes(
            category="pottery",
            material=["clay"],
            colors=["brown"],
            short_description="Clay pot",
            long_description="Traditional pot",
            region_of_origin="Khurja, Uttar Pradesh"
        )
        
        result = build_long_description(extracted)
        
        assert "Region of Origin" in result
        assert "Khurja, Uttar Pradesh" in result


class TestMapCategoryToOndc:
    """Test map_category_to_ondc function"""
    
    def test_exact_match(self):
        """Test exact category match"""
        assert map_category_to_ondc("handloom saree") == "Fashion:Ethnic Wear:Sarees"
        assert map_category_to_ondc("pottery") == "Home & Decor:Handicrafts:Pottery"
        assert map_category_to_ondc("jewelry") == "Fashion:Jewelry:Handcrafted"
    
    def test_case_insensitive(self):
        """Test case-insensitive matching"""
        assert map_category_to_ondc("POTTERY") == "Home & Decor:Handicrafts:Pottery"
        assert map_category_to_ondc("Handloom Saree") == "Fashion:Ethnic Wear:Sarees"
    
    def test_partial_match(self):
        """Test partial category matching"""
        assert map_category_to_ondc("silk saree") == "Fashion:Ethnic Wear:Sarees"
        assert map_category_to_ondc("clay pottery") == "Home & Decor:Handicrafts:Pottery"
    
    def test_unknown_category(self):
        """Test fallback for unknown categories"""
        assert map_category_to_ondc("unknown product") == "General:Handicrafts"
        assert map_category_to_ondc("") == "General:Handicrafts"
        assert map_category_to_ondc(None) == "General:Handicrafts"


class TestGenerateItemId:
    """Test generate_item_id function"""
    
    def test_deterministic_id(self):
        """Test that same attributes produce same ID"""
        extracted1 = ExtractedAttributes(
            category="pottery",
            subcategory="terracotta",
            material=["clay"],
            colors=["brown"],
            price={"value": 500, "currency": "INR"},
            short_description="Clay pot",
            long_description="Handmade pot"
        )
        
        extracted2 = ExtractedAttributes(
            category="pottery",
            subcategory="terracotta",
            material=["clay"],
            colors=["brown"],
            price={"value": 500, "currency": "INR"},
            short_description="Clay pot",
            long_description="Handmade pot"
        )
        
        id1 = generate_item_id(extracted1)
        id2 = generate_item_id(extracted2)
        
        assert id1 == id2
        assert id1.startswith("item_")
    
    def test_different_attributes_different_id(self):
        """Test that different attributes produce different IDs"""
        extracted1 = ExtractedAttributes(
            category="pottery",
            material=["clay"],
            colors=["brown"],
            price={"value": 500, "currency": "INR"},
            short_description="Clay pot",
            long_description="Handmade pot"
        )
        
        extracted2 = ExtractedAttributes(
            category="pottery",
            material=["clay"],
            colors=["red"],  # Different color
            price={"value": 500, "currency": "INR"},
            short_description="Clay pot",
            long_description="Handmade pot"
        )
        
        id1 = generate_item_id(extracted1)
        id2 = generate_item_id(extracted2)
        
        assert id1 != id2
    
    def test_material_order_independence(self):
        """Test that material order doesn't affect ID"""
        extracted1 = ExtractedAttributes(
            category="saree",
            material=["silk", "cotton"],
            colors=["red"],
            price={"value": 1000, "currency": "INR"},
            short_description="Saree",
            long_description="Silk saree"
        )
        
        extracted2 = ExtractedAttributes(
            category="saree",
            material=["cotton", "silk"],  # Different order
            colors=["red"],
            price={"value": 1000, "currency": "INR"},
            short_description="Saree",
            long_description="Silk saree"
        )
        
        id1 = generate_item_id(extracted1)
        id2 = generate_item_id(extracted2)
        
        assert id1 == id2


class TestBuildTags:
    """Test _build_tags function"""
    
    def test_basic_tags(self):
        """Test basic tag building"""
        extracted = ExtractedAttributes(
            category="pottery",
            material=["clay", "terracotta"],
            colors=["brown", "red"],
            short_description="Clay pot",
            long_description="Handmade pot"
        )
        
        tags = _build_tags(extracted)
        
        assert tags["material"] == "clay,terracotta"
        assert tags["color"] == "brown,red"
    
    def test_tags_with_dimensions(self):
        """Test tags include dimensions"""
        extracted = ExtractedAttributes(
            category="pottery",
            material=["clay"],
            colors=["brown"],
            dimensions={"length": 20, "width": 15, "height": 10, "unit": "cm"},
            short_description="Clay pot",
            long_description="Handmade pot"
        )
        
        tags = _build_tags(extracted)
        
        assert tags["length"] == "20 cm"
        assert tags["width"] == "15 cm"
        assert tags["height"] == "10 cm"
    
    def test_tags_with_weight(self):
        """Test tags include weight"""
        extracted = ExtractedAttributes(
            category="pottery",
            material=["clay"],
            colors=["brown"],
            weight={"value": 500, "unit": "g"},
            short_description="Clay pot",
            long_description="Handmade pot"
        )
        
        tags = _build_tags(extracted)
        
        assert tags["weight"] == "500 g"
    
    def test_tags_with_csi(self):
        """Test tags include CSI information"""
        csi = CSI(
            vernacular_term="मिट्टी",
            transliteration="Mitti",
            english_context="Clay",
            cultural_significance="Traditional material"
        )
        
        extracted = ExtractedAttributes(
            category="pottery",
            material=["clay"],
            colors=["brown"],
            short_description="Clay pot",
            long_description="Handmade pot",
            csis=[csi]
        )
        
        tags = _build_tags(extracted)
        
        assert tags["csi_1_term"] == "मिट्टी"
        assert tags["csi_1_transliteration"] == "Mitti"
        assert tags["csi_1_context"] == "Clay"
