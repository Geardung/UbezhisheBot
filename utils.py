from datetime import datetime
from typing import Union
import discord, os, json



def get_embeds(name: str, timestamps: Union[list[datetime], None] = None, **kwargs) -> list[discord.Embed]:

    def build_embeds(js:dict):
        
        embeds = []
        
        for key, value in js.items():
            
            if key == "embeds":

                for embed_js in value:
                    
                    new_embed = discord.Embed()

                    for key, value in embed_js.items():
                        
                        try:
                            
                            if key == "author": 
                                print(f"DEBUG -> Processing author: {value} (type: {type(value)})")
                                try:
                                    if isinstance(value, dict):
                                        name = value.get("name", discord.embeds.EmptyEmbed)
                                        url = value.get("url", discord.embeds.EmptyEmbed)
                                        icon_url = value.get("icon_url", discord.embeds.EmptyEmbed)
                                        print(f"DEBUG -> Author dict values: name={name}, url={url}, icon_url={icon_url}")
                                        try:
                                            new_embed.set_author(name=name, url=url, icon_url=icon_url)
                                            print("DEBUG -> Author set successfully")
                                        except Exception as e:
                                            print(f"DEBUG -> Error setting author: {str(e)}")
                                    else:
                                        print(f"DEBUG -> Author simple value: {value}")
                                        try:
                                            new_embed.set_author(name=str(value))
                                            print("DEBUG -> Author set successfully")
                                        except Exception as e:
                                            print(f"DEBUG -> Error setting author: {str(e)}")
                                except Exception as e:
                                    print(f"DEBUG -> Error processing author: {str(e)}")
                            
                            elif key == "footer": 
                                print(f"DEBUG -> Processing footer: {value} (type: {type(value)})")
                                try:
                                    if isinstance(value, dict):
                                        text = value.get("text", discord.embeds.EmptyEmbed)
                                        icon_url = value.get("icon_url", discord.embeds.EmptyEmbed)
                                        print(f"DEBUG -> Footer dict values: text={text}, icon_url={icon_url}")
                                        try:
                                            new_embed.set_footer(text=text, icon_url=icon_url)
                                            print("DEBUG -> Footer set successfully")
                                        except Exception as e:
                                            print(f"DEBUG -> Error setting footer: {str(e)}")
                                    else:
                                        print(f"DEBUG -> Footer simple value: {value}")
                                        try:
                                            new_embed.set_footer(text=str(value))
                                            print("DEBUG -> Footer set successfully")
                                        except Exception as e:
                                            print(f"DEBUG -> Error setting footer: {str(e)}")
                                except Exception as e:
                                    print(f"DEBUG -> Error processing footer: {str(e)}")

                            elif key == "fields":
                                
                                for field in value:
                                    
                                    new_embed.add_field(name= field.get("name", discord.embeds.EmptyEmbed), 
                                                        value= field.get("value", discord.embeds.EmptyEmbed), 
                                                        inline= field.get("inline", False))

                            elif key == "color": new_embed.color = discord.Colour(int(value.lstrip("#"), 16)) if value.get("color", False) else discord.Color.embed_background()
                            
                            elif key == "thumbnail": 
                                print(f"DEBUG -> Processing thumbnail: {value} (type: {type(value)})")
                                try:
                                    if isinstance(value, dict):
                                        url = value.get("url", discord.embeds.EmptyEmbed)
                                        print(f"DEBUG -> Thumbnail dict value: url={url}")
                                        try:
                                            new_embed.set_thumbnail(url=url)
                                            print("DEBUG -> Thumbnail set successfully")
                                        except Exception as e:
                                            print(f"DEBUG -> Error setting thumbnail: {str(e)}")
                                    else:
                                        print(f"DEBUG -> Thumbnail simple value: {value}")
                                        try:
                                            new_embed.set_thumbnail(url=str(value))
                                            print("DEBUG -> Thumbnail set successfully")
                                        except Exception as e:
                                            print(f"DEBUG -> Error setting thumbnail: {str(e)}")
                                except Exception as e:
                                    print(f"DEBUG -> Error processing thumbnail: {str(e)}")

                            elif key == "image": new_embed.set_image(url= value.get("url", discord.embeds.EmptyEmbed))
                            
                            elif key == "id": pass
                            
                            else: setattr(new_embed, key, value or discord.embeds.EmptyEmbed)
                            
                        except:
                            print("ERROR -> ", key, value)

                    embeds.append(new_embed)

            elif key == "content": pass

        return embeds
    
    path = "./embeds/" + name + ".json"
    
    if not os.path.exists(path): return get_embeds("error", trace_id="#TODO сделать создание Trace_Id для этого случая")
    
    with open(path, encoding="utf-8") as f:
        
        raw_diction = f.read()
        
        for var, val in kwargs.items(): raw_diction = raw_diction.replace("%"+var+"%", str(val))
        
        diction = json.loads(raw_diction)
        
        ready_embeds = build_embeds(diction)
        
        if timestamps and len(timestamps) != len(ready_embeds): return get_embeds("error", trace_id="#TODO сделать создание Trace_Id для этого случая")
        elif timestamps:
            for i, ts in enumerate(timestamps):
                
                if ts: ready_embeds[i].timestamp = ts
        
        return ready_embeds
    
    